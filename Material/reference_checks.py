"""Independent small-matrix regression oracles for mathematical_results.md.

Run: python tests/reference_checks.py
Dependency: NumPy.  These tests do not replace proofs or a production simulator.
Arc (x,y) means y -> x.  Edge M is column-stochastic; vertex P is row-stochastic.
"""
from __future__ import annotations
import unittest
from dataclasses import dataclass
import numpy as np
from numpy.testing import assert_allclose

ATOL = 2e-10

def close(a, b, atol=ATOL):
    assert_allclose(a, b, atol=atol, rtol=ATOL)

def proj(v):
    return np.outer(v, np.conjugate(v))

def density(n, seed=5):
    rng = np.random.default_rng(seed)
    a = rng.normal(size=(n,n)) + 1j*rng.normal(size=(n,n))
    r = a @ a.conj().T
    return r / np.trace(r)

def unitary(n, seed):
    rng = np.random.default_rng(seed)
    a = rng.normal(size=(n,n)) + 1j*rng.normal(size=(n,n))
    return np.linalg.qr(a)[0]

def trnorm(a):
    return float(np.abs(np.linalg.eigvalsh((a+a.conj().T)/2)).sum())

def stationary(P):
    n = P.shape[0]
    p = np.linalg.solve(np.eye(n)-P.T+np.ones((n,n)), np.ones(n))
    return p/p.sum()

def poisson_variance(P, f):
    pi = stationary(P)
    g = np.asarray(f, dtype=float)-pi @ f
    h = np.linalg.solve(np.eye(len(pi))-P+np.ones((len(pi),1))*pi, g)
    return float(pi @ (h*h-(P@h)**2))

@dataclass
class Model:
    neighbors: dict[int, list[int]]
    coins: dict[int, np.ndarray]

    def __post_init__(self):
        self.vertices = list(self.neighbors)
        if self.vertices != list(range(len(self.vertices))):
            raise ValueError('Reference helper requires vertices 0,...,m-1 in that order.')
        for x, ns in self.neighbors.items():
            if x in ns or len(ns)!=len(set(ns)):
                raise ValueError('Reference Model requires a simple loopless graph.')
            if any(x not in self.neighbors[y] for y in ns):
                raise ValueError('Graph must be undirected.')
            S = np.asarray(self.coins[x], dtype=complex)
            if S.shape != (len(ns),len(ns)):
                raise ValueError('Wrong coin shape.')
            close(S.conj().T@S, np.eye(len(ns)))
            self.coins[x] = S
        if len(self.vertices) < 2:
            raise ValueError('Reference simple graph must have at least two vertices.')
        reached = {self.vertices[0]}
        stack = [self.vertices[0]]
        while stack:
            x = stack.pop()
            for y in self.neighbors[x]:
                if y not in reached:
                    reached.add(y)
                    stack.append(y)
        if len(reached) != len(self.vertices):
            raise ValueError('Reference helper requires a connected graph.')
        self.arcs = [(x,y) for x in self.vertices for y in self.neighbors[x]]
        self.index = {e:i for i,e in enumerate(self.arcs)}
        self.d = len(self.arcs)
        self.m = len(self.vertices)
        self.inc = {x:[self.index[x,y] for y in self.neighbors[x]] for x in self.vertices}
        self.out = {x:[self.index[y,x] for y in self.neighbors[x]] for x in self.vertices}
        self.U = np.zeros((self.d,self.d), dtype=complex)
        self.F = np.zeros((self.d,self.d))
        self.C = np.zeros((self.d,self.d), dtype=complex)
        self.B = np.zeros((self.d,self.d))
        for x in self.vertices:
            self.U[np.ix_(self.out[x],self.inc[x])] = self.coins[x]
            self.C[np.ix_(self.inc[x],self.inc[x])] = self.coins[x]
            self.B[np.ix_(self.inc[x],self.inc[x])] = abs(self.coins[x])**2
        for (x,y),i in self.index.items():
            self.F[self.index[y,x],i]=1
        self.M = abs(self.U)**2
        self.K=[]
        self.PI=[]
        self.PO=[]
        for x in self.vertices:
            p = np.zeros((self.d,self.d)); p[self.inc[x],self.inc[x]]=1
            o = np.zeros_like(p); o[self.out[x],self.out[x]]=1
            self.PI.append(p); self.PO.append(o); self.K.append(self.U@p)
        self.atoms = [proj(self.U[:,i]) for i in range(self.d)]

    def phi(self, a):
        return sum((k@a@k.conj().T for k in self.K), np.zeros_like(a,dtype=complex))

    def dephase_in(self, a):
        return sum((p@a@p for p in self.PI), np.zeros_like(a,dtype=complex))

    def q2(self, rho):
        q=np.zeros(self.d)
        for x in self.vertices:
            block=rho[np.ix_(self.inc[x],self.inc[x])]
            b=self.coins[x]@block@self.coins[x].conj().T
            q[self.out[x]]=np.diag(b).real
        return q

    def mean(self, q):
        return (self.U*np.asarray(q)[None,:])@self.U.conj().T

    def superoperator(self):
        # Column-major vectorization: vec(K A K*) = (conj K tensor K) vec A.
        return sum((np.kron(k.conj(),k) for k in self.K), np.zeros((self.d**2,self.d**2),complex))

H=np.array([[1,1],[-1,1]],complex)/np.sqrt(2)

def path3(center=None):
    return Model({0:[1],1:[0,2],2:[1]}, {0:np.ones((1,1)),1:H.copy() if center is None else center,2:np.ones((1,1))})

def triangle(r=.25, swapped=False):
    S=np.array([[np.sqrt(r),np.sqrt(1-r)],[np.sqrt(1-r),-np.sqrt(r)]],complex)
    if swapped: S=S[:,[1,0]]
    return Model({0:[1,2],1:[0,2],2:[0,1]},{x:S.copy() for x in range(3)})

def random_triangle():
    return Model({0:[1,2],1:[0,2],2:[0,1]},{x:unitary(2,70+x) for x in range(3)})

def dft_model(neighbors):
    coins={}
    for x,ns in neighbors.items():
        n=len(ns); j=np.arange(n)
        coins[x]=np.exp(-2j*np.pi*np.outer(j,j)/n)/np.sqrt(n)
    return Model(neighbors,coins)

def vertex_preparations(model, omega=None, beta=None):
    if omega is None:
        omega={x:np.ones(len(model.neighbors[x]))/np.sqrt(len(model.neighbors[x])) for x in model.vertices}
    if beta is None: beta=np.zeros(model.m)
    R=np.zeros((model.m,model.d),complex)
    theta=np.zeros((model.m,model.m),complex)
    for x in model.vertices:
        close(np.vdot(omega[x],omega[x]),1)
        R[x,model.inc[x]]=np.conj(omega[x])
        v=model.coins[x]@omega[x]
        for j,z in enumerate(model.neighbors[x]):
            theta[z,x]=np.conj(omega[z][model.neighbors[z].index(x)])*v[j]
    chi=theta.copy()
    s=np.sum(abs(theta)**2,axis=0)
    if np.any(s>1+ATOL): raise ValueError('Invalid preparation norm.')
    chi[np.arange(model.m),np.arange(model.m)]=np.exp(1j*np.asarray(beta))*np.sqrt(np.maximum(0,1-s))
    return chi,theta,R

def vertex_channel(chi,a):
    return (chi*np.diag(a)[None,:])@chi.conj().T

def gram(chi,r=1):
    return abs(chi.conj().T@chi)**(2*r)

def mmd_canonical(U,V):
    d=U.shape[0]
    return 2/d**2*(d-np.sum(abs(U.conj().T@V)**4))

class MathematicalRegression(unittest.TestCase):
    def test_T01_unitarity_and_flip(self):
        a=random_triangle(); close(a.U.conj().T@a.U,np.eye(a.d)); close(a.F@a.F,np.eye(a.d)); close(a.U,a.F@a.C)

    def test_T02_local_unitary_application(self):
        a=random_triangle(); v=unitary(a.d,19)[:,0]; out=np.zeros(a.d,complex)
        for x in a.vertices: out[a.out[x]]=a.coins[x]@v[a.inc[x]]
        close(out,a.U@v); close(np.vdot(out,out),1)
        rho=density(a.d); close(np.linalg.eigvalsh(a.U@rho@a.U.conj().T),np.linalg.eigvalsh(rho))

    def test_T03_unitary_cesaro_degeneracy(self):
        U=np.diag([1,1,-1]); rho=density(3); r=(rho+U@rho@U)/2
        expected=rho.copy(); expected[:2,2]=0; expected[2,:2]=0
        close(r,expected); close(r[0,1],rho[0,1])

    def test_T04_star_block_square(self):
        a=path3(); order=[a.index[e] for e in [(1,0),(1,2),(0,1),(2,1)]]
        U=a.U[np.ix_(order,order)]; zero=np.zeros((2,2)); eye=np.eye(2)
        close(U,np.block([[zero,eye],[H,zero]])); close(U@U,np.block([[H,zero],[zero,H]]))

    def test_T05_kraus_and_channel(self):
        a=random_triangle(); I=np.eye(a.d); rho=density(a.d)
        close(sum(k.conj().T@k for k in a.K),I); close(sum(k@k.conj().T for k in a.K),I)
        close(a.phi(rho),a.U@a.dephase_in(rho)@a.U.conj().T)
        close(np.trace(a.phi(rho)),1); self.assertGreaterEqual(np.linalg.eigvalsh(a.phi(rho)).min(),-ATOL)

    def test_T06_two_step_products(self):
        a=path3()
        for x in a.vertices:
            for y in a.vertices:
                prod=a.K[x]@a.K[y]
                if (x,y) in a.index:
                    e=np.eye(a.d)[:,a.index[x,y]]
                    close(prod,a.U@proj(e)@a.U); self.assertEqual(np.linalg.matrix_rank(prod,tol=1e-9),1)
                else: close(prod,0)

    def test_T07_mixed_input_two_step_purity(self):
        a=path3(); rho=np.eye(a.d)/a.d
        one=a.K[1]@rho@a.K[1].conj().T; one/=np.trace(one)
        close(np.trace(one@one),.5)
        for (x,y),j in a.index.items():
            W=a.K[x]@a.K[y]; out=W@rho@W.conj().T
            normalized=out/np.trace(out); close(normalized,a.atoms[j]); close(np.trace(normalized@normalized),1)

    def test_T08_initial_coherences_and_reachability(self):
        a=path3(); v=np.zeros(a.d,complex); v[a.inc[1]]=np.array([1,1])/np.sqrt(2)
        w=v.copy(); w[a.inc[1][1]]*=-1
        close(np.diag(proj(v)),np.diag(proj(w))); self.assertGreater(np.linalg.norm(a.q2(proj(v))-a.q2(proj(w))),1)
        for j in range(a.d):
            e=np.eye(a.d)[:,j]; rho=a.U.conj().T@proj(e)@a.U
            close(a.q2(rho),e)

    def test_T09_q2_mean_and_time_offset(self):
        a=random_triangle(); rho=density(a.d,31); q=a.q2(rho)
        close(q,np.diag(a.U@rho@a.U.conj().T).real); close(q,np.diag(a.phi(rho)).real)
        dense=a.phi(a.phi(rho))
        for n in range(2,7):
            close(dense,a.mean(q)); close(np.diag(dense).real,a.M@q)
            q=a.M@q; dense=a.phi(dense)

    def test_T10_markov_transition_and_intertwining(self):
        a=random_triangle(); close(a.M.sum(0),1); close(a.M.sum(1),1); close(a.M,a.F@a.B)
        for j,sigma in enumerate(a.atoms): close(a.phi(sigma),a.mean(a.M[:,j]))

    def test_T11_observable_reconstruction(self):
        a=random_triangle(); q=np.arange(1,a.d+1,dtype=float); q/=q.sum(); A=density(a.d,11)
        values=np.array([np.trace(A@s) for s in a.atoms]); close(q@values,np.trace(A@a.mean(q)))
        close(np.trace(a.mean(q)@a.mean(q)),q@q)

    def test_T12_T3_hadamard_matrix(self):
        a=path3(); order=[a.index[e] for e in [(0,1),(2,1),(1,0),(1,2)]]
        M=a.M[np.ix_(order,order)]
        close(M,[[0,0,.5,.5],[0,0,.5,.5],[1,0,0,0],[0,1,0,0]])
        self.assertEqual(np.linalg.matrix_rank(M),3); self.assertEqual(np.linalg.matrix_rank(M@M),2)
        close(a.mean(np.ones(4)/4),np.eye(4)/4)

    def test_T13_identity_and_swap_classes(self):
        a=path3(np.eye(2)); close(a.M@a.M,np.eye(4))
        q=np.zeros(4);q[[a.index[0,1],a.index[1,0]]]=.5;close(a.M@q,q)
        b=path3(np.array([[0,1],[1,0]]));close(np.linalg.matrix_power(b.M,4),np.eye(4))
        self.assertGreater(np.linalg.norm(b.M@b.M-np.eye(4)),1)

    def test_T14_trace_norm_identities(self):
        a=path3(); q=np.array([.1,.2,.3,.4]); p=np.ones(4)/4
        close(trnorm(a.mean(q)-a.mean(p)),np.abs(q-p).sum())
        for j in range(4):
            close(trnorm(a.atoms[j]-np.eye(4)/4),1.5)
            for i in np.flatnonzero(a.M[:,j]>1e-12): close(trnorm(a.atoms[i]-a.atoms[j]),2)

    def test_T15_channel_ranks(self):
        a=path3(); L=a.superoperator()
        self.assertEqual(np.linalg.matrix_rank(L,tol=1e-9),6)
        for n in range(2,6):
            self.assertEqual(np.linalg.matrix_rank(np.linalg.matrix_power(L,n),tol=1e-9),np.linalg.matrix_rank(np.linalg.matrix_power(a.M,n-2),tol=1e-9))

    def test_T16_superoperator_adjoint_product(self):
        a=random_triangle(); L=a.superoperator(); DI=sum(np.kron(p,p) for p in a.PI)
        close(L.conj().T@L,DI)

    def test_T17_poisson_variances(self):
        for r in [0,.2,.5,.8]:
            M=np.array([[0,0,r,1-r],[0,0,1-r,r],[1,0,0,0],[0,1,0,0]])
            close(poisson_variance(M.T,np.array([1,0,0,0.])),r/(8*(1-r)))
        P=np.array([[2/3,1/3],[1/3,2/3]]);close(poisson_variance(P,np.array([1.,0.])),.5)

    def test_T18_empirical_error_spectrum(self):
        a=path3(); L=400; power=np.eye(4); total=0.
        for t in range(1,L):
            power=power@a.M;total+=(L-t)*(np.trace(power)-1)
        err=(1-1/4)/L+2/(4*L*L)*total
        close(L*err,.5,atol=.003)
        vals=np.linalg.eigvals(a.M);v=sum((1-abs(z)**2)/abs(1-z)**2 for z in vals if abs(z-1)>1e-8)/4
        close(v,.5)

    def test_T19_one_and_two_step_norms(self):
        a=triangle(); Pi=np.ones((6,6))/6
        close(np.linalg.norm(a.M-Pi,2),1);self.assertLess(np.linalg.norm(a.M@a.M-Pi,2),1-1e-5)
        b=path3();close(np.linalg.norm(b.M@b.M-np.ones((4,4))/4,2),1)

    def test_T20_flat_adjacency_reduction(self):
        a=triangle(.5);J=np.zeros((6,3))
        for x in a.vertices:J[a.inc[x],x]=1/np.sqrt(2)
        A=J.T@a.F@J;close(A,(np.ones((3,3))-np.eye(3))/2)
        for n in range(1,6):
            close(np.linalg.matrix_power(a.M,n),a.F@J@np.linalg.matrix_power(A,n-1)@J.T)
            close(np.linalg.norm(np.linalg.matrix_power(a.M,n)-np.ones((6,6))/6,2),.5**(n-1))

    def test_T21_same_measure_pair_law(self):
        a=triangle(.25);b=triangle(.25,True);p=np.arange(6)
        for ids in a.inc.values():p[ids]=ids[::-1]
        R=np.eye(6)[:,p];close(b.U,a.U@R);close(b.M,a.M@R)
        for e in range(6):close(b.atoms[e],a.atoms[p[e]])
        common=R@b.M@R.T;close(common,R@a.M)
        close(.5*np.abs((a.M-common)/6).sum(),1)

    def test_T22_same_measure_different_spectral_rate(self):
        a=triangle(.25);b=triangle(.25,True)
        def rate(M):return max(abs(z) for z in np.linalg.eigvals(M) if abs(z-1)>1e-8)
        close(rate(a.M),1/np.sqrt(2));close(rate(b.M),(1+np.sqrt(33))/8)
        close(np.linalg.svd(a.M,compute_uv=False),np.linalg.svd(b.M,compute_uv=False))

    def test_T23_flip_reversibility(self):
        a=random_triangle();close(a.M,a.F@a.M.T@a.F)
        self.assertGreater(np.linalg.norm(a.M-a.M.T),.1)

    def test_T24_parallel_arcs_counterexample(self):
        # Basis (target0,source1,port0/1), then reverse arcs.
        F=np.block([[np.zeros((2,2)),np.eye(2)],[np.eye(2),np.zeros((2,2))]])
        P0=np.diag([1,1,0,0]);P1=np.eye(4)-P0;K0=F@P0;K1=F@P1
        W=K1@K0;self.assertEqual(np.linalg.matrix_rank(W),2)
        rho=P0/2
        for k in [K0,K1,K0,K1]:
            rho=k@rho@k.T;rho/=np.trace(rho);close(np.trace(rho@rho),.5)

    def test_T25_vertex_construction(self):
        a=random_triangle();chi,theta,R=vertex_preparations(a,beta=[.1,.4,-.2])
        close(R@R.conj().T,np.eye(3));close(theta,R@a.U@R.conj().T)
        close(np.sum(abs(chi)**2,axis=0),1)
        rho=density(3);close(np.trace(vertex_channel(chi,rho)),1)

    def test_T26_complex_boundary_conjugation(self):
        a=random_triangle();omega={x:unitary(2,100+x)[:,0] for x in a.vertices}
        chi,theta,R=vertex_preparations(a,omega,beta=[0,.4,.2]);close(theta,R@a.U@R.conj().T)
        wrong=np.zeros_like(theta)
        for x in a.vertices:
            v=a.coins[x]@omega[x]
            for j,z in enumerate(a.neighbors[x]):wrong[z,x]=omega[z][a.neighbors[z].index(x)]*v[j]
        self.assertGreater(np.linalg.norm(theta-wrong),.1)

    def test_T27_raw_compression_trace_preserving_counterexample(self):
        ns={0:[1],1:[0,2],2:[1,3],3:[2]};a=Model(ns,{x:np.eye(len(v)) for x,v in ns.items()})
        omega={0:np.array([1]),1:np.array([1,0]),2:np.array([0,1]),3:np.array([1])}
        chi,theta,R=vertex_preparations(a,omega);close(np.sum(abs(theta)**2,axis=0),1);close(chi,theta)
        close(theta,np.eye(4)[:,[1,0,3,2]])

    def test_T28_vertex_conditional_purity(self):
        a=random_triangle();chi,_,_=vertex_preparations(a);rho=density(3)
        for x in range(3):
            G=np.outer(chi[:,x],np.eye(3)[x]);r=G@rho@G.conj().T
            close(np.trace(r),rho[x,x]);close(r/np.trace(r),proj(chi[:,x]))

    def test_T29_vertex_mean_and_born_timing(self):
        a=random_triangle();chi,_,_=vertex_preparations(a,beta=[.3,.5,.9]);P=(abs(chi)**2).T;rho=density(3,50)
        q=np.diag(rho).real.copy();dense=vertex_channel(chi,rho)
        for n in range(1,7):
            close(dense,(chi*q[None,:])@chi.conj().T);close(np.diag(dense).real,q@P)
            q=q@P;dense=vertex_channel(chi,dense)

    def test_T30_duplicate_atoms_lumping(self):
        v=np.ones(2)/np.sqrt(2);chi=np.column_stack([v,v]);P=(abs(chi)**2).T
        close(P[0],P[1]);rho1=(chi*np.array([1,0])[None,:])@chi.conj().T
        rho2=(chi*np.array([0,1])[None,:])@chi.conj().T;close(rho1,rho2)
        pi=stationary(P);close(pi,[.5,.5]);close(np.diag(rho1).real,pi)

    def test_T31_vertex_stationarity_and_norm_sandwich(self):
        a=random_triangle();chi,_,_=vertex_preparations(a,beta=[.2,-.4,.6]);P=(abs(chi)**2).T;pi=stationary(P)
        rho=(chi*pi[None,:])@chi.conj().T;close(vertex_channel(chi,rho),rho);close(np.diag(rho).real,pi)
        q=np.array([.1,.2,.7]);diff=(chi*(q-pi)[None,:])@chi.conj().T
        self.assertLessEqual(np.abs(q@P-pi).sum(),trnorm(diff)+ATOL)
        self.assertLessEqual(trnorm(diff),np.abs(q-pi).sum()+ATOL)

    def test_T32_dft_transient_basin_weights(self):
        ns={0:[1],1:[0,2],2:[1,3],3:[4,2],4:[3]};a=dft_model(ns);chi,_,_=vertex_preparations(a);P=(abs(chi)**2).T
        expected=np.array([[.5,.5,0,0,0],[1,0,0,0,0],[0,.5,.5,0,0],[0,0,0,0,1],[0,0,0,.5,.5]])
        close(P,expected);r0=np.eye(5)[2];close(r0[[0,1,3,4]].sum(),0)
        close(r0@np.linalg.matrix_power(P,100),[2/3,1/3,0,0,0])

    def test_T33_bistochastic_not_unital(self):
        chi=np.array([[1,1],[1,np.exp(.5j)]])/np.sqrt(2);P=(abs(chi)**2).T
        close(P.sum(0),1);close(P.sum(1),1)
        self.assertGreater(np.linalg.norm(vertex_channel(chi,np.eye(2))-np.eye(2)),.1)
        rho=vertex_channel(chi,np.eye(2)/2);self.assertGreater(np.trace(rho@rho).real,.5)

    def test_T34_grover_alpha_invariance(self):
        ns={0:[1],1:[0,2],2:[1]};out=[]
        for alpha in [0,.7,np.pi]:
            coins={}
            for x,v in ns.items():
                w=np.ones(len(v))/np.sqrt(len(v));Q=proj(w);coins[x]=Q+np.exp(1j*alpha)*(np.eye(len(v))-Q)
            chi,_,_=vertex_preparations(Model(ns,coins),beta=[.1,.2,.3]);out.append(chi)
        for chi in out:close(chi,out[0])
        P=(abs(out[0])**2).T;close(P,P.T);self.assertTrue(np.any(np.diag(P)>1e-5))

    def test_T35_edge_rkhs_and_masa(self):
        a=path3(np.eye(2));b=path3();close(mmd_canonical(a.U,b.U),1/8)
        def super_dephase(atoms):
            return sum(np.outer(s.reshape(-1,order='F'),s.reshape(-1,order='F').conj()) for s in atoms)
        delta=super_dephase(a.atoms)-super_dephase(b.atoms)
        close(np.linalg.norm(delta,'fro')**2/16,1/8)
        comm=sum(np.linalg.norm(p@q-q@p,'fro')**2 for p in a.atoms for q in b.atoms)
        close(comm/16,1/8)
        th=np.pi/2;S=np.array([[1,1],[-np.exp(1j*th),np.exp(1j*th)]])/np.sqrt(2);c=path3(S)
        close(b.M,c.M);self.assertGreater(mmd_canonical(b.U,c.U),.01)

    def test_T36_tensor_gram_identifiability(self):
        chi=np.array([[1,0,1,1,1],[0,1,1,1j,2+1j]],complex);chi/=np.linalg.norm(chi,axis=0)
        self.assertLess(np.linalg.matrix_rank(gram(chi,1),tol=1e-9),5)
        K=gram(chi,4);self.assertGreater(np.linalg.eigvalsh(K).min(),1e-6)
        q=np.arange(1,6,dtype=float);q/=q.sum();close(np.linalg.solve(K,(q@K).T),q)

    def test_T37_higher_moment_factorization(self):
        a=random_triangle();chi,_,_=vertex_preparations(a);P=(abs(chi)**2).T;K=gram(chi)
        self.assertGreaterEqual(np.linalg.eigvalsh(K-P@P.T).min(),-ATOL)
        q=np.array([.2,.3,.5]);atoms=[proj(chi[:,i]) for i in range(3)]
        mom=sum(q[i]*np.kron(atoms[i],atoms[i]) for i in range(3))
        partial=np.trace(mom.reshape(3,3,3,3),axis1=1,axis2=3)
        close(partial,sum(q[i]*atoms[i] for i in range(3)));close(np.diag(partial).real,q@P)

    def test_T38_pair_reconstruction_and_triangle_reversal(self):
        chi=np.array([[1,0,1],[1,1,0],[0,1,1]],float)/np.sqrt(2);K=gram(chi,2)
        C=np.array([[0,1,0],[0,0,1],[1,0,0.]])
        T=(np.eye(3)+C)/2;pi=np.ones(3)/3;Q=np.diag(pi)@T;B=K@Q@K
        recovered=np.linalg.solve(K,np.linalg.solve(K,B).T).T;close(recovered,Q)
        A=Q-Q.T;close(np.trace(A.T@K@A@K),75/512)

    def test_T39_lyapunov_and_residual(self):
        T=triangle(.25).M.T;n=len(T);pi=np.ones(n)/n;Pi=np.ones((n,1))*pi;A=T-Pi;K=np.eye(n)
        term=K.copy();Hsum=np.zeros_like(K)
        for _ in range(500):
            Hsum+=term;term=A@term@A.T
            if np.linalg.norm(term)<1e-14:break
        close(Hsum-A@Hsum@A.T,K)
        q=np.arange(1,n+1,dtype=float);q/=q.sum();b=q-pi
        close((b@T)@Hsum@(b@T),b@Hsum@b-b@K@b)
        Z=np.linalg.inv(np.eye(n)-T+Pi);close((q-q@T)@Z,q-pi)

    def test_T40_measure_gauge_not_channel_gauge(self):
        a=path3();b=path3(H@np.diag([1,-1]));c=path3(np.exp(.4j)*H)
        close(a.M,b.M);close(mmd_canonical(a.U,b.U),0)
        v=np.zeros(4,complex);v[a.inc[1]]=np.ones(2)/np.sqrt(2);rho=proj(v)
        self.assertGreater(np.linalg.norm(a.phi(rho)-b.phi(rho)),.5);close(a.phi(rho),c.phi(rho))

    def test_T41_perturbation_bound(self):
        a=triangle(.25);b=triangle(.3);delta=max(np.linalg.norm(a.coins[x]-b.coins[x],2) for x in a.vertices)
        close(np.linalg.norm(a.U-b.U,2),delta);r1=density(6);r2=r1.copy()
        for n in range(1,5):
            r1=a.phi(r1);r2=b.phi(r2)
            self.assertLessEqual(trnorm(r1-r2),2*n*delta+ATOL)
            self.assertLessEqual(np.linalg.norm(np.linalg.matrix_power(a.U,n)-np.linalg.matrix_power(b.U,n),2),n*delta+ATOL)

    def test_T42_equation_431_probability_factor(self):
        a=path3();rho=np.eye(4)/4;y=1;x=0
        un1=a.K[y]@rho@a.K[y].conj().T;p1=np.trace(un1).real;r1=un1/p1
        conditional=a.K[x]@r1@a.K[x].conj().T
        W=a.K[x]@a.K[y];joint=W@rho@W.conj().T
        close(np.trace(conditional),.5);close(np.trace(joint),.25);close(joint,p1*conditional)
        self.assertGreater(np.linalg.norm(joint-conditional),.1)

if __name__=='__main__':
    unittest.main(verbosity=2)
