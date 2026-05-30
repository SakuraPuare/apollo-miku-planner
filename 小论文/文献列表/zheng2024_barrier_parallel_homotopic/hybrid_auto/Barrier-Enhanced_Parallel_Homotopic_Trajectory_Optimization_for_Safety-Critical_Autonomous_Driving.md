# Barrier-Enhanced Parallel Homotopic Trajectory Optimization for Safety-Critical Autonomous Driving

Lei Zheng , Rui Yang , Michael Yu Wang , Fellow, IEEE, and Jun Ma , Member, IEEE

Abstract— Enforcing safety while preventing overly conservative behaviors is essential for autonomous vehicles to achieve high task performance. In this paper, we propose a barrier-enhanced parallel homotopic trajectory optimization (BPHTO) approach with the over-relaxed alternating direction method of multipliers (ADMM) for real-time integrated decision-making and planning. To facilitate safety interactions between the ego vehicle (EV) and surrounding vehicles, a spatiotemporal safety module exhibiting bi-convexity is developed on the basis of barrier function. Varying barrier coefficients are adopted for different time steps in a planning horizon to account for the motion uncertainties of surrounding HVs and mitigate conservative behaviors. Additionally, we exploit the discrete characteristics of driving maneuvers to initialize nominal behavior-oriented free-end homotopic trajectories based on reachability analysis, and each trajectory is locally constrained to a specific driving maneuver while sharing the same task objectives. By leveraging the bi-convexity of the safety module and the kinematics of the EV, we formulate the BPHTO as a bi-convex optimization problem. Then constraint transcription and the over-relaxed ADMM are employed to streamline the optimization process, such that multiple trajectories are generated in real time with feasibility guarantees. Through a series of experiments, the proposed development demonstrates improved task accuracy, stability, and consistency in various traffic scenarios using synthetic and real-world traffic datasets.

Index Terms— Autonomous driving, trajectory optimization, spatiotemporal safety, alternating direction method of multipliers (ADMM), integrated decision-making and planning.

# I. INTRODUCTION

ENSURING the safety of autonomous vehicles in dynamic environments is crucial. The imperative lies in developing a motion planning strategy that ensures safety while

Received 15 February 2024; revised 30 September 2024; accepted 7 November 2024. Date of publication 5 December 2024; date of current version 4 February 2025. This work was supported by the National Natural Science Foundation of China under Grant 62303390. The Associate Editor for this article was Y. Huang. (Corresponding author: Jun Ma.)

Lei Zheng and Rui Yang are with the Robotics and Autonomous Systems Thrust, The Hong Kong University of Science and Technology (Guangzhou), Guangzhou 511453, China (e-mail: lzheng135@connect.ust.hk; ryang253@connect.hkust-gz.edu.cn).

Michael Yu Wang is with the School of Engineering, Great Bay University, Dongguan 523000, China (e-mail: mywang@gbu.edu.cn).

Jun Ma is with the Robotics and Autonomous Systems Thrust, The Hong Kong University of Science and Technology (Guangzhou), Guangzhou 511453, China, and also with the Division of Emerging Interdisciplinary Areas, The Hong Kong University of Science and Technology, Hong Kong SAR, China (e-mail: jun.ma@ust.hk).

Data is available on-line at https://sites.google.com/view/bphto?pli=1 and https://youtu.be/ensRDOYWeZ4.

Digital Object Identifier 10.1109/TITS.2024.3498457

keeping high task performance [1], [2], [3]. This necessitates the strategy to generate safe, feasible, comfortable, and energy-efficient trajectories in real-time replan iterations [4], [5], [6]. However, achieving these characteristics in plans poses substantial challenges. Firstly, challenges stem from the inherently multi-modal nature of motion patterns exhibited by human-driven vehicles (HVs), such as sudden deceleration and cut-in behaviors [7], [8], [9]. These challenges pose formidable threats to the safety and driving stability of the autonomous ego vehicle (EV) when interacting with HVs, particularly in dense traffic. Secondly, the non-holonomic kinematic constraints of the EV, coupled with safety constraints, introduce nonlinearity and non-convexity into the planning problem, making it challenging to find feasible trajectories in real time [10], [11], [12]. In this context, the optimization landscape features multiple local minima and non-smooth regions, substantially impacting the convergence and performance of gradient-based optimization algorithms [13]. Thirdly, the swift replanning behavior, especially in selecting the target driving lane, may lead to frequent lane changes, adversely affecting driving safety and consistency. These challenges underscore the crucial requirement for an efficient motion planning framework to tackle the intricacies of autonomous vehicle navigation.

In general, motion planning for autonomous driving applications can be attempted in a sequential manner. A decisionmaking module, known as a behavior planner, handles high-level decisions and produces a coarse trajectory, and then a trajectory planner takes these decisions and generates a smooth and feasible trajectory [14], [15]. Since the driving maneuvers in the decision-making process are inherently discrete variables (e.g., lane changing and lane keeping), existing behavior planners typically address this challenge by solving the mixed-integer programming (MIP) problem [14], [16], [17], which is NP-hard [18]. This complexity becomes particularly critical when the EV needs to operate in multi-lane driving scenarios under dense traffic. To tackle these issues, Finite State Machine (FSM) [19], [20], [21] has been proposed to select the appropriate driving maneuver. Following this, an optimization-based trajectory planner is developed to generate the target trajectory for the EV. Nevertheless, these decoupled motion planning architectures may result in a planned trajectory deviating from the target maneuver, leading to either conservative or aggressive actions [22].

Rather than tackling the decision-making and trajectoryplanning problems separately, the optimal control framework has been employed to integrate discrete decision variables into a continuous optimization problem [23], [24], [25], [26], [27]. In [23], a mixed-integer model predictive control (MPC) scheme with a fail-safe strategy is developed to facilitate the safe interaction of the EV with surrounding vehicles. However, solving this MIP problem poses computational challenges, especially in practical multi-lane autonomous driving scenarios. To streamline the optimization process, this work employs relaxation and constraint enforcement techniques to transform the MIP problem into a nonlinear programming (NLP) problem within a nonlinear MPC (NMPC) framework [24], [25]. In [28], an optimal control framework integrating behavior and trajectory planning is developed to facilitate the navigation of the EV through a multi-lane dense traffic scenario, leveraging a multi-threading technique. While these studies utilize offthe-shelf solvers to achieve nearly real-time performance, it is worth noting that these solvers may struggle to compute a feasible solution due to the nonlinear, non-convex characteristics of the optimization problem. To enhance feasibility, existing interaction-aware MPC techniques either reinitialize the optimal control problem with zero as a starting point [29] or introduce slack variables when the collision avoidance constraint is not feasible [9].

To facilitate safety interactions between the EV and surrounding HVs, the reachability analysis [30] and control barrier function (CBF) [31] have been utilized to construct collision avoidance constraints in autonomous driving. In [32], [33], the fail-safe strategy has been designed as a safety filter for the EV based on the obstacle-free reachable set computed through reachability analysis. Although reachability analysis provides formal safety guarantees for the EV, it has the drawback that unsafe regions may expand rapidly over time. Consequently, the planned motions tend to be overly conservative. Alternatively, the CBF with proactive collision avoidance properties is integrated as a safety constraint in the NMPC framework to enhance safety interactions [21], [34]. However, solving the NMPC becomes computationally burdensome over a long planning horizon (typically exceeding 50 steps) for practical autonomous driving tasks due to the necessity of solving the inverse of the Hessian matrix [35]. It is worth noting that these works assume constant speeds for surrounding vehicles, potentially compromising the safety of the EV, especially when surrounding HVs exhibit nondeterministic behaviors, such as abrupt lane changes.

Considering the uncertain behaviors of surrounding HVs, researchers have extensively implemented partially observable Markov decision process [36], [37], [38], [39] to address the motion uncertainties of surrounding vehicles. While these works showcase the ability to handle the multi-modal behaviors of surrounding HVs, solving such problems becomes computationally intractable as the problem size increases [40]. An alternative approach involves employing multiple trajectory optimization methods to handle the multi-modal behaviors of the HVs in a receding horizon planning manner [41], [42], [43], [44]. In [41], a branch MPC is proposed to optimize over a scenario tree representing possible future behaviors of surrounding uncontrolled agents. Although this method shows promise in facilitating safe interactions between the EV and surrounding HVs, the optimized trajectories tend to be overly conservative, thereby compromising driving efficiency. In [42], Batch-MPC is proposed for real-time highway autonomous driving through optimizing multiple trajectories based on the alternating minimization algorithm [45]. However, Batch-MPC frequently switches between local optimal trajectories, leading to frequent lane changes and compromising driving consistency. To overcome these significant impediments, a topology-driven planner is developed [44]. It iteratively plans multiple evasive trajectories in distinct homotopy classes, ensuring the planner does not change the homotopy class throughout the optimization process. Additionally, a consistent parameter is introduced in the decision-making module to prevent frequent switching of the homotopy class of the executed trajectory. To further consider the interaction between the EV and HVs, an interactive joint planner (IJP) based on homotopy trajectory optimization is developed [43]. The IJP simultaneously optimizes multiple free-end homotopy trajectories, each with a distinct endpoint, aiming to explore diverse motions and mitigate the local minima issue in non-convex optimization. However, none of these homotopic trajectory optimization approaches address the safety recovery of the EV, such as the recovery of a safe following distance after being abruptly cut in by other HVs.

In this paper, we present an integrated decision-making and planning scheme for safety-critical autonomous driving with a proposed Barrier-Enhanced Parallel Homotopic Trajectory Optimization (BPHTO) algorithm. The discrete driving maneuvers of the EV are utilized to construct behavior-oriented free-end homotopic trajectories based on reachability analysis. Subsequently, BPHTO integrates these nominal free-end homotopic trajectories, considering safety and stability, into a bi-convex optimization problem. To ensure feasibility and streamline the optimization process, we employ constraint transcription and the over-relaxed alternating direction method of multipliers (ADMM) [16] to enable real-time solving of this bi-convex optimization problem in a parallel manner.

The main contributions of this paper are summarized as follows:

• We propose a BPHTO algorithm to seamlessly integrate decision-making and planning for autonomous driving, which inherently blends discrete maneuver decisions into continuous parallel trajectory optimization. By leveraging reachability analysis, we devise a goal-sampling strategy with warm initialization to determine discrete maneuver homotopy for BPHTO in a receding horizon planning manner. This allows the EV to respond adeptly to surrounding HVs without compromising driving consistency.   
• We leverage the spatiotemporal information between the EV and HVs to design the spatiotemporal control barrier to enable proactive interaction between the EV and uncertain HVs with safety guarantees. By progressively increasing the barrier coefficient, we effectively account for the motion uncertainties of HVs, enabling the EV to take less conservative actions with safety assurances.

Moreover, a rigorous theoretical analysis demonstrates the robustness of safety, showcasing the asymptotic convergence of the EV from an unsafe state to a safe state in the sense of Lyapunov stability.

• We exploit the bi-convexity of the kinematics of the EV and the spatiotemporal control barrier to split the BPHTO into several low-dimensional Quadratic Programming (QP) subproblems through over-relaxed ADMM iterations. This strategic approach ensures a feasible solution and enables the EV to execute complex driving tasks in real time.   
• We thoroughly demonstrate the improved task performance and safety recovery achieved by our proposed framework through comparative simulations with stateof-the-art algorithms on the intelligent driver model (IDM) and recorded real-world traffic datasets.

The rest of this paper is structured as follows: The problem statement is introduced in Section II. Section III presents the spatiotemporal control barrier for ensuring the safety of the EV. The task-oriented motion for autonomous driving is described in Section IV. We derive a parallelizable optimization scheme BPHTO through over-relaxed ADMM iterations in Section V. The validation of the proposed algorithm applied to a safety-critical autonomous vehicle system, using both synthetic and real-world traffic data, is demonstrated in Section VI. A discussion of computational efficiency and driving consistency is presented in Section VII. Finally, a conclusion is drawn in Section VIII.

# II. PROBLEM STATEMENT

In this study, we consider multi-lane dense and cluttered driving scenarios, as depicted in Fig. 1. We adopt Dubin’s car model for the EV, with the yaw rate θ˙ and acceleration a as control inputs [43]. To facilitate smooth trajectory optimization, we expand the state vector to include control inputs and their derivatives:

$$
\mathbf {x} = [ p _ {x} \quad p _ {y} \quad \theta \quad \dot {\theta} \quad v \quad a _ {x} \quad a _ {y} \quad j _ {x} \quad j _ {y} ] ^ {T} \in \mathcal {X},
$$

where $p _ { x }$ and $p _ { y }$ denote the longitudinal and lateral positions of the EV in the global coordinate, respectively; v denotes the speed of the EV in the global coordinate; θ represents the heading angle of the EV; $a _ { x }$ and $a _ { y }$ denote the longitudinal and lateral accelerations in the global coordinate, respectively; $j _ { x }$ and $j _ { y }$ denote the longitudinal and lateral jerks in the global coordinate, respectively. In this safety-critical autonomous driving scenario, the autonomous EV encounters substantial challenges when interacting with multiple surrounding HVs that exhibit multi-modal behaviors, such as accelerations, decelerations, and lane changes. These complex interactions compromise driving efficiency and pose significant safety risks. Moreover, the frequent lane changes in this environment can adversely affect the overall driving comfort and jeopardize the safety of the EV. To address this complex problem, we make the following foundational assumptions and definitions:

Assumption 1 (Safety Responsibility [46]): When two vehicles are driving in the same direction, if the rear vehicle $c _ { r }$ hits the front vehicle $c _ { f }$ from behind, then the rear vehicle $c _ { r }$ is responsible for the accident.

![](images/54142970bf42e823c145eef0c0dd5792d6a525d77e9f13aea533166631fb41dc.jpg)

<details>
<summary>flowchart</summary>

```mermaid
graph TD
    A["Top Road Car"] --> B{Intended Motion}
    B -->|ξ = 1| C["Top Road Car"]
    B -->|ξ = 0| D["Bottom Road Car"]
    B -->|ξ = -1| E["Bottom Road Car"]
    style A fill:#f9f,stroke:#333
    style B fill:#bbf,stroke:#333
    style C fill:#dfd,stroke:#333
    style D fill:#dfd,stroke:#333
    style E fill:#dfd,stroke:#333
    subgraph Road Construction
        direction LR
        C -->|ξ = 1| B
        D -->|ξ = 0| B
        E -->|ξ = -1| B
    end
```
</details>

Fig. 1. Illustration of the motion of an EV (in red color) in a dynamic cluttered scenario with one lane under road construction ahead. The orange and blue vehicles represent perceived and unperceived HVs, respectively. The EV and the i-th HV are represented as ellipse-shaped convex compact set $\mathbb { X }$ and $\mathbb { O } _ { i } .$ , respectively. The solid red line with an arrow represents the intended trajectory of the EV, while other solid lines denote alternative free-end homotopic candidate trajectories of the EV. Each trajectory shares the same initial state and corresponds to a specific driving maneuver denoted as ξ , with values of {0, 1, −1}, representing lane-keeping, left-lane-change, and right-lane-change behaviors, respectively.

Assumption 2 (Perception Ability): An autonomous EV possesses the capability to gather accurate information regarding the current positions and velocities of the M nearest HVs.

Definition 1 (Free-End Homotopy [43]): Let $\tau _ { 1 } : \mathbb { R }  \mathcal { X }$ and $\tau _ { 2 } : \mathbb { R }  \mathcal { X }$ be two continuous trajectories that share the same start point but not necessarily the same endpoint. A continuous mapping 8 : $: [ 0 , 1 ] \times \mathbb { R } $ X is termed a free-end homotopy if it satisfies the following criteria:

• $\Phi ( 0 , \cdot ) = \tau _ { 1 } ( \cdot ) ,$   
• $\Phi ( 1 , \cdot ) = \tau _ { 2 } ( \cdot ) .$

If a free-end homotopy 8 exists between $\tau _ { 1 }$ and $\tau _ { 2 } ,$ then the two trajectories are said to be free-end homotopic, which is a generalization of homotopy as proven in [43].

We aim to develop an efficient integrated decision-making and planning framework for the EV, enabling safe and stable interactions with HVs while maintaining high task efficiency. This framework aims to simultaneously generate multiple free-end homotopic trajectories represented as

$$
\mathcal {T} := \left\{\mathbf {x} _ {k} ^ {(j)} \right\} _ {j = 1} ^ {N _ {c}}, k \in \mathcal {I} _ {0} ^ {N - 1}, \tag {1}
$$

where $\mathbf { x } _ { k } \in \mathcal { X } \subset \mathbb { R } ^ { n }$ denotes the state vector of the EV at time instant $k ; ~ N$ and $N _ { c }$ denote the planned time steps and the number of trajectories, respectively. Each free-end homotopic candidate trajectory $\tau _ { j } ~ = ~ \left\{ \mathbf { x } _ { k } ^ { ( j ) } \right\} _ { k = 1 } ^ { N } ~ \in ~ \mathcal { T }$ n ( j ) o N is elaborately k=1 designed and optimized to represent a specific discrete driving behavior $\xi \in \Xi$ , where $\Xi = \{ 0 , 1 , - 1 \}$ . Each behavior is aligned with a target driving lane, as illustrated in Fig. 1.

The integrated decision-making and planning framework can be formulated as a finite-constrained NLP problem over a horizon of N steps, as follows:

$$
\underset {\mathrm{T}} {\text { minimize }} \sum_ {j = 0} ^ {N _ {c} - 1} \sum_ {k = 0} ^ {N - 1} \mathcal {L} (\mathbf {x} _ {k} ^ {(j)}) + \phi (\mathbf {x} _ {N} ^ {(j)}) \tag {2a}
$$

$$
\text { s.t. } \quad \mathbf {x} _ {0} ^ {(j)} = \mathbf {x} (0), \tag {2b}
$$

$$
\mathbf {x} _ {N} ^ {(j)} \in \mathcal {X} _ {f} ^ {(j)}, \tag {2c}
$$

$$
\mathbf {x} _ {k + 1} ^ {(j)} = f ^ {E V} (\mathbf {x} _ {k} ^ {(j)}), \tag {2d}
$$

$$
\mathbf {O} _ {k + 1} ^ {(i)} = \zeta (\mathbf {O} _ {k} ^ {(i)}), \tag {2e}
$$

$$
\mathbf {d i s t} (\mathbb {X} _ {k} ^ {(j)}, \mathbb {O} _ {k} ^ {(i)}) > d _ {\text { safe }} ^ {(i)}, \tag {2f}
$$

$$
\mathbf {x} _ {k} ^ {(j)} \in \mathcal {X}, \tag {2g}
$$

$$
\forall k \in \mathcal {I} _ {0} ^ {N - 1}, j \in \mathcal {I} _ {0} ^ {N _ {c} - 1}, i \in \mathcal {I} _ {0} ^ {M - 1}.
$$

Here, $\mathcal { T } _ { 0 } ^ { N _ { c } - 1 }$ represents the set of consecutive integers from 0 to $\begin{array} { r } { N _ { c } - 1 ; \mathrm { T } = \left\{ \tau _ { 1 } ^ { T } , \tau _ { 2 } ^ { T } , \dots , \tau _ { N _ { c } } ^ { T } \right\} } \end{array}$ τ 2 ， , represents the optimized trajectories; M denotes the anticipated number of HVs in trajectory optimization; x0 denotes the observed initial state vector of the EV; $f ^ { E V }$ describes the non-holonomic motion constraints for the EV, ensuring that the $\mathrm { E V } \mathbf { \bar { s } }$ motion adheres to its physical limitations. Each $\mathbf { O } ^ { ( i ) }$ denotes the state vector of the i-th HV in the environment, and $\zeta$ characterizes the predicted motion for these HVs. The term $\mathcal { L }$ represents the running cost, designed to encode specific task requirements, such as smoothness and task accuracy, and $\phi$ is the terminal cost function for stabilization consideration.

Remark 1: The target state set $\chi _ { f } ^ { ( j ) }$ is designed to optimize the j -th candidate trajectory to a desired driving lane, with the attendant outcome of a driving behavior ξ.

Remark 2: The optimization problem $( 2 a ) – ( 2 g )$ yields meticulously optimized and feasible free-end homotopic trajectories, each of which is associated with a specific driving behavior. It effectively blends discrete maneuver decisions with continuous trajectory generation for motion planning.

The challenges of designing and optimizing this NLP problem are fourfold:

(1) Safety: The motion of HVs exhibits multi-modal driving behaviors that are difficult to predict accurately. This challenge makes it difficult to strictly satisfy safety constraints (2f) over a long planning horizon,   
(2) Feasibility: The non-holonomic constraint (2e) and safety constraint (2f) are typically nonlinear and nonconvex, posing significant challenges for finding feasible solutions.   
(3) Computational Efficiency: The proposed approach must efficiently optimize multiple nominal free-end homotopic trajectories in real time during interactions with multiple HVs, ensuring prompt decision-making and adaptability to dynamic environments.   
(4) Safety-Performance Trade-off: Balancing multiple intricate objectives and constraints, such as safety, motion stability, task accuracy, and control limits, is essential in designing an NLP problem for the EV. The presence of uncertainties in the motion of surrounding HVs adds further complexity to the problem, making it more challenging to achieve the desired task performance while avoiding collisions, frequent lane changes, and overly cautious behaviors.

# III. SPATIOTEMPORAL CONTROL BARRIER

# A. Trajectory Parameterization

In this study, each trajectory is optimized over a compact time interval with a finite duration of T . To obtain optimal

and smoothly controllable homotopic trajectories for the EV, we employ a representation based on Bézier curves [47], [48], facilitating continuous differentiable and optimized trajectories for the EV. For an m dimensional and n-th order Bézier curve, the representation is given by:

$$
\mathbf {C} ^ {(j)} (\nu) = \sum_ {i = 0} ^ {n} B _ {i, n} (\nu) \mathbf {P} _ {i} ^ {(j)}, j \in \mathcal {I} _ {0} ^ {N _ {c} - 1}, \tag {3}
$$

where P( j ) $\mathbf { P } _ { i } ^ { ( j ) } \in \mathbb { R } ^ { m }$ represents control points or Bézier coefficients to be optimized for the j -th trajectory. Specifically, we define P( j) $\mathbf { P } _ { i } ^ { ( j ) } = [ c _ { x , i } ^ { ( j ) } \quad c _ { y , i } ^ { ( j ) } \quad c _ { \theta , i } ^ { ( j ) } ] ^ { T }$ = [c( j )x ,i c( j )]T , where $c _ { x , i } ^ { ( j ) } , c _ { y , i } ^ { ( \bar { j } ) }$ , and $c _ { \theta , i } ^ { ( j ) }$ denote the coefficients for the longitudinal position $p _ { x }$ , lateral position $p _ { y } ,$ , and heading angle θ, respectively. The Bernstein polynomial basis $B _ { i , n }$ is defined as

$$
B _ {i, n} (\nu) = \binom {n} {i} \nu^ {i} (1 - \nu) ^ {n - i}, \tag {4}
$$

where $\textstyle \nu = { \frac { t - t _ { 0 } } { T } } \in [ 0 , 1 ]$ is the parameter varying from 0 to 1. Here, t0 represents the initial time, $t = t _ { 0 } + k \delta t$ is the current time instant of the trajectory, k denotes discrete time steps, and $\delta t = T / N$ is the corresponding discrete time interval.

As a result, the trajectory sequences can be expressed as follows:

$$
\left\{\mathbf {C} _ {k} ^ {(j)} \right\} _ {k = 0} ^ {N - 1} = \mathbf {W} _ {P, j} ^ {T} \mathbf {W} _ {B}, j \in \mathcal {I} _ {0} ^ {N _ {c} - 1}, \tag {5}
$$

where $\mathbf { C } _ { k } ^ { ( j ) } ~ = ~ [ p _ { x , k } ^ { ( j ) } ~ p _ { y , k } ^ { ( j ) } ~ \theta _ { k } ^ { ( j ) } ] ^ { T }$ ( [ p x,k p y ,k represents the longitudinal position, lateral position, and heading angle for the j -th trajectory at time instant k; $\mathbf { W } _ { P , j } = \mathbf { \bar { \mathbf { P } } } _ { 0 } ^ { ( j ) } \mathbf { \bar { \mathbf { P } } } _ { 1 } ^ { ( j ) }$ $\mathbf { P } _ { n } ^ { ( j ) } ] ^ { T } \in \mathbb { R } ^ { ( n + 1 ) \times 3 }$ denotes the matrix of control points to be optimized; $\begin{array} { r l r } { { \bf W } _ { B } } & { { } = } & { [ { \bf B } _ { 0 } \mathrm { ~ \bf ~ B } _ { 1 } \mathrm { ~  ~ \cdot ~ } . . . \mathrm { ~ \bf ~ B } _ { n } ] ^ { T } \quad \in } \end{array}$ R(n+1)×N is a constant basis matrix, where $\begin{array} { r l } { \mathbf { B } _ { i } } & { { } = } \end{array}$ $[ B _ { i , n } ( \delta t ) \quad B _ { i , n } ( 2 \delta t ) \quad \cdots \quad B _ { i , n } ( N \delta t ) ] ^ { T } \quad \in \quad \mathbb { R } ^ { N }$ . We can derive this $C ^ { 1 }$ continuity trajectory (3) to get its velocity, acceleration, and jerk profiles. Note that the discrete integrator model inherent in high-order $( n ~ \geq ~ 4 )$ Bézier polynomial trajectories (3) constrain the motion of the EV.

# B. Spatiotemporal Control Barrier

To achieve high-performance safe driving, the EV must navigate to its goal state while avoiding collisions with nearby HVs that exhibit multi-modal behaviors. This necessitates the consideration of spatiotemporal relative positions and angles between the EV and surrounding HVs. While the safety constraint (2f) provides a sufficient but unnecessary condition for collision avoidance, strictly adhering to these constraints can typically result in overly cautious driving maneuvers, comprising task performance. In this subsection, we develop an efficient spatiotemporal control barrier for the EV. This spatiotemporal control barrier enables the EV to safely interact with uncertain surrounding HVs while avoiding overly cautious driving behaviors. Additionally, a rigorous robustness safety analysis is provided.

1) Safety Representations: The unsafe set, safe set, and interior safe set for the EV are defined as follows:

$$
O u t (\mathcal {S}) := \{\mathbf {x} \in \mathcal {X} \mid h (\mathbf {x}, \mathbf {O} ^ {(i)}) <   0, \forall i \in \mathcal {I} _ {0} ^ {M - 1} \}, \tag {6a}
$$

$$
\mathcal {S} := \{\mathbf {x} \in \mathcal {X} \mid h (\mathbf {x}, \mathbf {O} ^ {(i)}) \geq 0, \forall i \in \mathcal {I} _ {0} ^ {M - 1} \}, \tag {6b}
$$

$$
I n t (\mathcal {S}) := \{\mathbf {x} \in \mathcal {X} \mid h (\mathbf {x}, \mathbf {O} ^ {(i)}) > 0, \forall i \in \mathcal {I} _ {0} ^ {M - 1} \}, \tag {6c}
$$

where h is a discrete-time barrier function to facilitate safety interactions through the following definition:

Definition $2 \ ( l 4 9 l ) .$ : A function h is said to be a discretetime barrier function (BF) with respect to the set $S \ ( 6 a ) { - } ( 6 c ) ,$ , if there exists a barrier coefficient $\alpha _ { k } \in ( 0 , 1 )$ with $s \subset { \mathcal { X } } ,$ , such that

$$
\Delta h (\mathbf {x} _ {k}, \mathbf {O} _ {k} ^ {(i)}) + \alpha_ {k} h (\mathbf {x} _ {k - 1}, \mathbf {O} _ {k - 1} ^ {(i)}) > 0, \tag {7}
$$

where $\Delta h ( \mathbf x _ { k } , \mathbf O _ { k } ^ { ( i ) } ) : = h ( \mathbf x _ { k } , \mathbf O _ { k } ^ { ( i ) } ) - h ( \mathbf x _ { k - 1 } , \mathbf O _ { k - 1 } ^ { ( i ) } ) .$

Definition 3 (Forward Invariably Safe Set): Given an initial safe state $\mathbf { x } _ { 0 } \in { \mathcal { S } } ,$ a barrier function $h ,$ and the future trajectories of the M nearest HVs nO(i)k oT= $\mathbf { \bar { \Psi } } \left\{ \mathbf { O } _ { k } ^ { ( i ) } \right\} _ { k = 0 } ^ { T } , \forall i \in \mathcal { T } _ { 0 } ^ { M - 1 }$ , ∀i ∈ I M −10 , the set S is said to be a Forward Invariably Safe Set if, for all $k > 0 ,$ the following condition holds:

$$
h (\mathbf {x} _ {k}, \mathbf {O} _ {k} ^ {(i)}) \geq 0, \quad \forall i \in \mathcal {I} _ {0} ^ {M - 1}. \tag {8}
$$

2) Invariably Safety Constraints: Following the approach outlined in [42] and [50], we leverage the polar representation of Euclidean distance between the EV and surrounding HVs to obtain the following safety constraints:

$$
\left\{ \begin{array}{l} p _ {x, k} = o _ {x, k} ^ {(i)} + l _ {x} ^ {(i)} d _ {k} ^ {(i)} \cos (\omega_ {k} ^ {(i)}), \\ p _ {y, k} = o _ {y, k} ^ {(i)} + l _ {y} ^ {(i)} d _ {k} ^ {(i)} \sin (\omega_ {k} ^ {(i)}), \\ d _ {k} ^ {(i)} \geq 1, \forall i \in \mathcal {I} _ {0} ^ {M - 1}, \end{array} \right. \tag {9}
$$

where $p _ { x , k }$ and $p _ { y , k }$ represent the longitudinal and lateral positions of the EV at time instant k, respectively; $o _ { x , k } ^ { ( i ) }$ and $o _ { x , k } ^ { ( i ) }$ ox,k denote the longitudinal and lateral positions of the i-th surrounding HV at time instant k, respectively; $l _ { x } ^ { ( i ) }$ and $l _ { y } ^ { ( i ) }$ denote the length of major and minor axes of the safe ellipse, respectively. The variable $\omega _ { k } ^ { ( i ) } \in [ 0 , \pi ]$ denotes the angle of safe ellipse between the EV and i-th surrounding HV at time instant k.

Note that the variable $d _ { k } ^ { ( i ) }$ functions as a scaling factor influencing the size of the safety region associated with the i-th surrounding HV at time instant k. Larger values of $d _ { k } ^ { ( i ) }$ correspond to larger safety regions, promoting increased separation, while a value close to 1 indicates a more compact safety region, maintaining a non-zero separation distance for safety considerations.

Referring to [51], we can further formulate barrier function h with respect to the safety constraint (9) as

$$
h (\mathbf {x} _ {k}, \mathbf {O} _ {k} ^ {(i)}) = d _ {k} ^ {(i)} - 1. \tag {10}
$$

Hence, a BF constraint can be formulated to facilitate proactively collision avoidance as

$$
\Delta h (\mathbf {x} _ {k}, \mathbf {O} _ {k} ^ {(i)}) + \alpha_ {k} (h (\mathbf {x} _ {k - 1}, \mathbf {O} _ {k - 1} ^ {(i)}) > 0, \tag {11}
$$

which can be explicitly expressed as

$$
d _ {k} ^ {(i)} - 1 - (1 - \alpha_ {k}) (d _ {k - 1} ^ {(i)} - 1) > 0. \tag {12}
$$

The constraint (11) ensures that the EV with an initial safe state x0 ∈ S remains within the forward invariably safe set $s ,$ as elaborated in [52, Proposition 4].

As a result, we can transform the original safety constraint (9) into the following spatiotemporal control barrier safety constraint:

$$
\left\{ \begin{array}{l} p _ {x, k} = o _ {x, k} ^ {(i)} + l _ {x} ^ {(i)} d _ {k} ^ {(i)} \cos \left(\omega_ {k} ^ {(i)}\right), \\ p _ {y, k} = o _ {y, k} ^ {(i)} + l _ {y} ^ {(i)} d _ {k} ^ {(i)} \sin \left(\omega_ {k} ^ {(i)}\right), \\ \Delta h \left(\mathbf {x} _ {k}, \mathbf {O} _ {k} ^ {(i)}\right) + \alpha_ {k} h \left(\mathbf {x} _ {k - 1}, \mathbf {O} _ {k - 1} ^ {(i)}\right) > 0, \forall i \in \mathcal {I} _ {0} ^ {M - 1}. \end{array} \right. \tag {13}
$$

We can further derive the closed-form value of $\omega _ { k } ^ { ( i ) }$ ω as follows:

$$
\omega_ {k} ^ {(i)} = \arctan \left(l _ {x} ^ {(i)} (p _ {y, k} - o _ {y, k} ^ {(i)}), l _ {y} ^ {(i)} (p _ {x, k} - o _ {x, k} ^ {(i)})\right). \tag {14}
$$

Theorem 1: Let h be a discrete-time BF for the EV under Assumptions 1-2. Then, the EV, starting from an initial state $\mathbf { x } _ { k - 1 } ~ \in ~ I n t ( { \cal S } )$ , can proactively avoid collisions with surrounding HVs with guaranteed safety if the constraint (11) is satisfied.

Proof: Given an initial state $\mathbf { x } _ { k - 1 } \ \in \ I n t ( S )$ , we can derive the barrier function $h ( \mathbf { x } _ { k - 1 } , \mathbf { O } _ { k - 1 } ^ { ( i ) } ) > 0$ .

With Definition 2, we can express (11) as:

$$
h (\mathbf {x} _ {k}, \mathbf {O} _ {k} ^ {(i)}) > (1 - \alpha_ {k}) h (\mathbf {x} _ {k - 1}, \mathbf {O} _ {k - 1} ^ {(i)}), \tag {15}
$$

where $\alpha _ { k } \in ( 0 , 1 ) , \forall h \neq 0 .$ . This leads to the following result:

$$
h (\mathbf {x} _ {k}, \mathbf {O} _ {k} ^ {(i)}) > 0. \tag {16}
$$

As a result, the EV, starting from an initial safe state, remains within the safety set S.

Moreover, the parameter $\alpha _ { k } \in \mathbb { R } ^ { + }$ serves as a barrier coefficient that influences the changing rate of the safety function h during planning. If $\alpha _ { k } = 1$ , the safety constraint (13) reverts to its original form (9). Consequently, the constraint does not confine optimization until near safety violation $( h = 0 )$ . In contrast, smaller values of $\alpha _ { k }$ contribute to a more stable adjustment of the safety barrier, promoting proactive collision avoidance, as shown in [34] and [51]. Conversely, larger values allow for more aggressive maneuvers and less conservative driving behaviors. This completes the proof of Theorem 1.

Remark 3: In dense traffic, accurately predicting the motion of surrounding HVs is challenging, particularly in subsequent planning steps. To tackle this challenge, we adopt a strategy where the parameter αk gradually increases throughout the planning horizon N . This approach strikes a balance between task performance and safety. As αk grows, it expands the feasible state space and diminishes the influence of safety constraints on the NLP problem (2) over time, as outlined in [34]. Consequently, the planner can prioritize the driving task in the short term while ensuring the EV’s safety in the long term, leading to less conservative actions.

3) Robustness of Safety: In certain situations, such as abrupt lane changes by surrounding HVs with nonstationary dynamics, safety constraints (13) may be violated. However, this violation does not necessarily result in a collision with the EV since the axis lengths of the safe ellipse typically exceed the specified collision size limit. In this subsection, we further investigate the robustness of the spatiotemporal control barrier safety constraints (13) regarding safety recovery. The analysis is conducted with an initial unsafe state $\mathbf { x } _ { 0 } \in O u t ( S )$ , aiming to guide the EV to asymptotically converge to the safe set S from an unsafe state $O u t ( S )$ .

Theorem 2: Let h be a discrete-time BF for the EV under Assumptions 1-2. Then, the unsafe state $\mathbf { x } _ { k - 1 } ~ \in ~ O u t ( \mathcal { S } )$ asymptotically converges to the forward invariably safe set $s$ if the following constraint is satisfied:

$$
\Delta h (\mathbf {x} _ {k}, \mathbf {O} _ {k} ^ {(i)}) + \alpha_ {k} h (\mathbf {x} _ {k - 1}, \mathbf {O} _ {k - 1} ^ {(i)}) \geq 0. \tag {17}
$$

Proof: With the barrier function h, we define a positive definite Lyapunov function $V : \mathbb { R } ^ { n }  \mathbb { R }$ as follows:

$$
V \left(\mathbf {x} _ {k}, \mathbf {O} _ {k} ^ {(i)}\right) = \left\{ \begin{array}{l l} 0 & \text { if } \mathbf {x} _ {k} \in \mathcal {S}, \\ | h \left(\mathbf {x} _ {k}, \mathbf {O} _ {k} ^ {(i)}\right) | ^ {2} & \text { if } \mathbf {x} _ {k} \in O u t (\mathcal {S}). \end{array} \right. \tag {18}
$$

Based on the constraint (17), we can derive the following inequality:

$$
\begin{array}{l} | h (\mathbf {x} _ {k}, \mathbf {O} _ {k} ^ {(i)}) | ^ {2} \leq | h (\mathbf {x} _ {k - 1}, \mathbf {O} _ {k - 1} ^ {(i)}) - \alpha_ {k} h (\mathbf {x} _ {k - 1}, \mathbf {O} _ {k - 1} ^ {(i)}) | ^ {2} \\ = (1 - \alpha_ {k}) ^ {2} | h (\mathbf {x} _ {k - 1}, \mathbf {O} _ {k - 1} ^ {(i)}) | ^ {2}, \tag {19} \\ \end{array}
$$

where $h < 0 .$

Utilizing the properties of the Lyapunov function, we can derive:

$$
\begin{array}{l} \Delta V (\mathbf {x} _ {k}, \mathbf {O} _ {k} ^ {(i)}) = V (\mathbf {x} _ {k}, \mathbf {O} _ {k} ^ {(i)}) - V (\mathbf {x} _ {k - 1}, \mathbf {O} _ {k - 1} ^ {(i)}) \\ = | h (\mathbf {x} _ {k}, \mathbf {O} _ {k} ^ {(i)}) | ^ {2} - | h (\mathbf {x} _ {k - 1}, \mathbf {O} _ {k - 1} ^ {(i)}) | ^ {2} \\ \leq (1 - \alpha_ {k}) ^ {2} | h (\mathbf {x} _ {k - 1}, \mathbf {O} _ {k - 1} ^ {(i)}) | ^ {2} \\ - \left| h (\mathbf {x} _ {k - 1}, \mathbf {O} _ {k - 1} ^ {(i)}) \right| ^ {2} \\ \leq ((1 - \alpha_ {k}) ^ {2} - 1) | h (\mathbf {x} _ {k - 1}, \mathbf {O} _ {k - 1} ^ {(i)}) | ^ {2} \\ = ((1 - \alpha_ {k}) ^ {2} - 1) V (\mathbf {x} _ {k - 1}, \mathbf {O} _ {k - 1} ^ {(i)}). \tag {20} \\ \end{array}
$$

Consequently, the following inequality holds:

$$
\Delta V (\mathbf {x} _ {k}, \mathbf {O} _ {k} ^ {(i)}) \leq - c _ {k} V (\mathbf {x} _ {k - 1}, \mathbf {O} _ {k - 1} ^ {(i)}), \tag {21}
$$

where $c _ { k } = ( 1 - ( 1 - \alpha _ { k } ) ^ { 2 } ) \in ( 0 , 1 )$ .

If there exists no solution that can stay identically in $s ,$ other than the trivial solution $x _ { k } ~ \in ~ { \mathcal { S } }$ , then the origin is asymptotically stable. This result indicates that the state of the EV with $h \ : < 0$ will asymptotically converge to the safe set S in the sense of Lyapunov stability. This completes the proof of Theorem 2. □

Note that the parameter $\alpha _ { k } \in \mathbb { R } ^ { + }$ adjusts the aggressiveness of safety recovery. We adopt a progressively increasing $\alpha _ { k } \in$ $\mathbb { R } ^ { + }$ along the planning horizon, allowing for a stable safety recovery.

# IV. TASK-ORIENTED AND MANEUVER-ORIENTED MOTION

In this study, each maneuver is aligned with a candidate trajectory directed towards a specific driving lane, resulting in maneuver homotopy, as illustrated in Fig. 1. The optimization process involves sampling target points $\left\{ \mathbf { x } _ { g } ^ { ( j ) } \right\} _ { j = 1 } ^ { N _ { c } }$ ( j ) o Nc within the current and neighboring lanes. These points guide trajectory optimization to remedy the local minimum issue in the non-convex motion space, considering dynamic feasibility and driving stability.

# A. Dynamic Feasibility

The engine force of the ego vehicle limits the acceleration and braking as follows:

$$
a _ {x, \min} \leq a _ {x, k} ^ {(j)} \leq a _ {x, \max}, \forall k \in \mathcal {I} _ {0} ^ {N - 1}, j \in \mathcal {I} _ {0} ^ {N _ {c} - 1}, \tag {22a}
$$

$$
a _ {y, \min} \leq a _ {y, k} ^ {(j)} \leq a _ {y, \max}, \forall k \in \mathcal {I} _ {0} ^ {N - 1}, j \in \mathcal {I} _ {0} ^ {N _ {c} - 1}, \tag {22b}
$$

where $a _ { x , \mathrm { m a x } }$ and $a _ { y , \mathrm { m a x } }$ denote the maximum longitudinal and lateral acceleration, respectively; $a _ { x }$ ,min and $a _ { y , \mathrm { m i n } }$ denote the minimum longitudinal and lateral deceleration, respectively. The motion of the EV is further constrained by nonholonomic constraints:

$$
\left\{ \begin{array}{l l} \dot {p} _ {x, k} ^ {(j)} - & v _ {k} ^ {(j)} \cos (\theta_ {k} ^ {(j)}) = 0, \forall k \in \mathcal {I} _ {0} ^ {N - 1}, j \in \mathcal {I} _ {0} ^ {N _ {c} - 1}, \\ \dot {p} _ {y, k} ^ {(j)} - & v _ {k} ^ {(j)} \sin (\theta_ {k} ^ {(j)}) = 0, \forall k \in \mathcal {I} _ {0} ^ {N - 1}, j \in \mathcal {I} _ {0} ^ {N _ {c} - 1}. \end{array} \right. \tag {23}
$$

Following the approach outlined in [further derive the following constraint of $\theta _ { k } ^ { \left( j \right) }$ and [51], we can and closed-form solution of v( j )k $v _ { k } ^ { ( j ) }$

$$
\theta_ {k} ^ {(j)} - \arctan \left(\frac {\dot {p} _ {y , k} ^ {(j)}}{\dot {p} _ {x , k} ^ {(j)}}\right) = 0, \forall k \in \mathcal {I} _ {0} ^ {N - 1}, j \in \mathcal {I} _ {0} ^ {N _ {c} - 1}, \tag {24}
$$

$$
v _ {k} ^ {(j)} = \sqrt {(\dot {p} _ {x , k} ^ {(j)}) ^ {2} + (\dot {p} _ {y , k} ^ {(j)}) ^ {2}},
$$

$$
\forall k \in \mathcal {I} _ {0} ^ {N - 1}, j \in \mathcal {I} _ {0} ^ {N _ {c} - 1}. \tag {25}
$$

# B. Task-Oriented Motion

To generate parallel free-end homotopic trajectories, we enforce the final longitudinal position $\bar { p } _ { x , N } ^ { ( j ) }$ and lateral position $p _ { y , N } ^ { ( j ) }$ p y , N of each trajectory to align with target sampling points. To achieve this, we introduce the following state constraints to guide the optimized trajectory to the desired state with continuity consideration:

$$
p _ {x, 0} ^ {(j)} = p _ {x} (0), \quad p _ {y, 0} ^ {(j)} = p _ {y} (0), \tag {26a}
$$

$$
v _ {x, 0} ^ {(j)} = v (0) \cos (\theta (0)), \quad v _ {y, 0} ^ {(j)} = v (0) \sin (\theta (0)), \tag {26b}
$$

$$
p _ {x, N} ^ {(j)} = p _ {x, g} ^ {(j)}, \quad p _ {y, N} ^ {(j)} = p _ {y, g} ^ {(j)}, \tag {26c}
$$

where $j \in \mathcal { T } _ { 0 } ^ { N _ { c } - 1 }$ ; v(0) and θ (0) represent the initial velocity and heading angle of the EV, respectively; $p _ { x } ( 0 )$ and $p _ { y } ( 0 )$ represent the initial position of the EV. The target position sampling mechanism to determine the target longitudinal position $p _ { x , g } ^ { ( j ) }$ and lateral position $p _ { y , g } ^ { ( j ) }$ of the j -th candidate trajectory will be elaborated in Section IV-C.

To ensure a stable driving mode during the generation of each maneuver homotopy, we enforce the planned trajectory to exhibit a tiny heading angle and yaw rate, as specified by the following terminal driving stability constraints:

$$
\theta_ {0} ^ {(j)} = \theta (0), \quad \dot {\theta} _ {0} ^ {(j)} = \dot {\theta} (0), \tag {27a}
$$

$$
\theta_ {N} ^ {(j)} = 0, \quad \dot {\theta} _ {N} ^ {(j)} = 0, \tag {27b}
$$

for all $j ~ \in ~ \mathcal { T } _ { 0 } ^ { N _ { c } - 1 }$ ∈ I Nc−10 , where $\dot { \theta } ( 0 )$ represents the initial yaw rate of the EV. Furthermore, to achieve a comfortable driving experience, the jerk needs to be constrained as follows:

$$
j _ {x, \min} \leq j _ {x, k} ^ {(j)} \leq j _ {x, \max}, \forall k \in \mathcal {I} _ {0} ^ {N - 1}, j \in \mathcal {I} _ {0} ^ {N _ {c} - 1}, \tag {28a}
$$

$$
j _ {y, \min} \leq j _ {y, k} ^ {(j)} \leq j _ {y, \max}, \forall k \in \mathcal {I} _ {0} ^ {N - 1}, j \in \mathcal {I} _ {0} ^ {N _ {c} - 1}, \tag {28b}
$$

where $j _ { x , \mathrm { m a x } }$ and $j _ { x , \mathrm { m i n } }$ denote the maximum and minimum allowable longitudinal acceleration, respectively; $j _ { y , \mathrm { m a x } }$ and $j _ { y , \mathrm { m i n } }$ denote the maximum and minimum allowable lateral deceleration, respectively. The comfortable longitudinal and lateral jerk values have been comprehensively discussed in [53].

# C. Sampling Points Generation

To enhance the quality of free-end homotopic trajectory optimization, the target position in (26c) for each trajectory should account for not only the current state vector of the EV but also the state limits of the EV and the future motion of surrounding HVs.

In this study, we develop a warm initialization strategy to determine maneuver homotopy in a receding horizon planning manner to facilitate driving consistency. Specifically, in each replanning step, the lateral goal position $p _ { y , g } ^ { ( \bar { j } ) } , \forall j \in \bar { \mathcal { T } } _ { 0 } ^ { N _ { c } - 1 }$ I0 , for each nominal free-end homotopic trajectory, evolves based on the last optimal trajectory and maneuver as follows:

$$
\mathbf {P} _ {y, g} = p _ {y, g} ^ {*} + \delta \mathbf {y}. \tag {29}
$$

Here, $\mathbf { P } _ { y , g } = \left\{ p _ { y , g } ^ { ( j ) } \right\} _ { i = 1 } ^ { N _ { c } } \in \mathbb { R } ^ { 1 \times N _ { c } }$ ( j ) oNc g j =1 represents the target lateral goal vector for $p _ { y , g } ^ { * }$ denotes the lateral position of the optimal trajectory $N _ { c }$ nominal free-end homotopic trajectories. $\xi ^ { * }$ in Section $\mathrm { V } { \mathrm { - } } \mathrm { C } .$ . The maneuver adjustment vector $\delta \mathbf { y } \in \mathbb { R } ^ { 1 \times N _ { c } }$ is typically designed as a symmetrical vector centered around zero. It includes positive, negative, and zero values to ensure alignment with the latest optimal maneuver, maintaining consistency and reliability in adjustments. For example, in Fig. 1, a mean value of zero indicates maintaining the last decision maneuver $( \xi = 0 )$ , negative values imply right lane changing $( \xi = - 1 )$ , generating trajectories below the current lane, while positive values denote left lane changing $( \xi = 1 )$ , generating trajectories above the current lane. Additionally, each element in $\mathbf { P } _ { y , g }$ is clipped using clip( $p _ { y , g } ^ { ( j ) } , p _ { y , \mathrm { m i n } } , p _ { y , \mathrm { m a x } } )$ to facilitate the EV in adjusting its lateral position to proactively avoid road construction areas.

Drawing inspiration from the double S velocity profile to generate a smooth acceleration profile for stable motion planning [54], we determine the longitudinal goal position $\bar { p _ { x , g } ^ { ( j ) } } , \forall \bar { j } \ \in \bar { \mathcal { T } } _ { 0 } ^ { \tilde { N } _ { c } - 1 }$ , based on reachability, task accuracy, and interaction safety between the EV and HVs.

Given the current longitudinal position $p _ { x , 0 }$ , velocity $v _ { x , 0 }$ , acceleration ${ a } _ { x , 0 }$ , desired velocity $v _ { d } .$ , the acceleration range defined in (22a), and the jerk range specified in (28a) for the EV, we can compute the target longitudinal position using the following criteria:

• The final longitudinal acceleration is set to zero.   
• $j _ { x , \mathrm { m a x } } = - j _ { x , \mathrm { m i n } } .$

As a result, we can obtain analytical solutions for the ideal longitudinal distance based on reachability analysis. For brevity, we consider a task where the initial velocity $v _ { x , 0 }$ is less than the desired velocity $v _ { d } ;$ and vice versa. Two cases can be distinguished, as follows:

• Case 1: The longitudinal acceleration increases linearly from an initial value $a _ { 0 }$ to $a _ { 1 }$ over the time interval $t ~ \in ~ [ t _ { 0 } , t _ { 1 } ]$ with the maximum longitudinal jerk $j _ { x }$ ,max. Subsequently, it decreases linearly to zero from $t \in [ t _ { 1 } , t _ { 2 } ]$ with the minimum longitudinal jerk $j _ { x , \mathrm { m i n } }$ and maintains zero acceleration from $t \in [ t _ { 2 } , T ]$ until the end.   
• Case 2: The acceleration increases linearly from an initial value a0 to the maximum value $a _ { x , \mathrm { m a x } }$ over the time interval $t \in [ t _ { 0 } , t _ { a } ]$ with the maximum longitudinal jerk $j _ { x , \mathrm { m a x } } .$ . It then maintains this maximum constant value from $t ~ \in ~ [ t _ { a } , t _ { c } ]$ and decreases linearly to zero from $t \in [ t _ { c } , T ]$ with the minimum longitudinal jerk $j _ { x , \mathrm { m i n } }$ .

We can get the corresponding analytical longitudinal distance changes $\delta p _ { \ j }$ x in Case 1 and Case 2 (see Appendix). Therefore, we can get the target longitudinal goal position vector for $N _ { c }$ free-end homotopic trajectories, as follows:

$$
\mathbf {P} _ {x, g} = p _ {x} + \delta \mathbf {x}, \tag {30}
$$

where $\mathbf { P } _ { x , g } = \left\{ p _ { x , g } ^ { ( j ) } \right\} _ { j = 1 } ^ { N _ { c } } \in \mathbb { R } ^ { 1 \times N _ { c } } ; p _ { x }$ n ( j ) oNc px ,g j =1 is the current longitudinal position of the EV; $\delta \mathbf { x } = \left\{ \delta p _ { x , g } ^ { ( j ) } \right\} _ { j = 1 } ^ { N _ { c } } \in \mathbb { R } ^ { 1 \times N _ { c } }$ nδ p( j )x ,g o j=1 , where the variable $\delta p _ { x , g } ^ { ( j ) }$ is initialized to $\delta p _ { x }$ at the beginning of each receding horizon planning. Additionally, it undergoes dynamic online adjustments to avoid collision-occupied regions with the following safety checking function $h _ { D } \colon$

$$
h _ {D} = \frac {\left(p _ {x , g} ^ {(j)} - o _ {x , N} ^ {(i)}\right) ^ {2}}{a _ {i} ^ {2}} + \frac {\left(p _ {y , g} ^ {(j)} - o _ {y , N} ^ {(i)}\right) ^ {2}}{b _ {i} ^ {2}} - 1, i \in \mathcal {I} _ {0} ^ {N _ {c} - 1}, \tag {31}
$$

where o(i )x,N $o _ { x , N } ^ { ( i ) }$ an d o(i ) $o _ { y , N } ^ { ( i ) }$ represent the predicted final longitudinal and lateral position of the i -th HVs, respectively; $a _ { i }$ and $b _ { i }$ denote the major and minor axis lengths of a safe ellipse for the interaction of the EV and i-th HV, respectively. The positive value of the safety checking function $h _ { D }$ denotes safety; and vice versa. The procedure is detailed in Algorithm 1.

Remark 4: In Case 2, when the desired velocity vd of the EV significantly exceeds its initial longitudinal speed $v _ { x , 0 } ,$ , there is a possibility that the EV may not reach the desired velocity vd within its planning horizon T . For instance, the high-speed EV got cut in by a low-speed HV in a cruise task. Our approach to determining the goal vector based on double S velocity optimization can facilitate stable driving under this condition.

# V. BARRIER-ENHANCED PARALLEL HOMOTOPIC TRAJECTORY OPTIMIZATION (BPHTO) WITH OVER-RELAXED ADMM

# A. Problem Reformulation

By incorporating spatiotemporal control barriers, dynamic feasibility, task-oriented motion constraints, we can reformulate the initial NLP $( 2 \mathrm { a } ) \mathrm { - } ( 2 \mathrm { g } )$ into the following bi-convex optimization problem:

$$
\min_ {\substack {\left\{\mathbf {C} _ {\theta}, \mathbf {C} _ {x}, \mathbf {C} _ {y} \right\} \\ \left\{\boldsymbol {\omega}, \mathbf {d} \right\}}} f (\mathbf {C} _ {\theta}) + g _ {x} (\mathbf {C} _ {x}) + g _ {y} (\mathbf {C} _ {y}) \tag{32a}
$$

$$
\text { s.   t. } \quad \mathbf {F} _ {0} \mathbf {C} _ {\theta} \in \mathcal {C} _ {0}, \mathbf {F} _ {f} \mathbf {C} _ {\theta} \in \mathcal {C} _ {f}, \tag {32b}
$$

# Algorithm 1 Sampling Points Generation

# 1: Parameters:

$v _ { d } \colon$ Desired longitudinal driving speed;

$a _ { x , \mathrm { m a x } } \mathrm { : }$ Maximum longitudinal acceleration;

$a _ { x , \mathrm { m i n } } \mathrm { : }$ Minimum longitudinal acceleration;

$j _ { x , \mathrm { { m a x } } } \colon$ Maximum longitudinal jerk;

$j _ { x , \mathrm { m i n } } \colon$ Minimum longitudinal jerk;

$\Delta d _ { x } \mathbf { \cdot }$ : Constant adjustment interval;

M: Number of the nearest $\mathrm { H V s ; }$

$\left\{ { \bf O } _ { 0 } ^ { ( i ) } \right\} _ { i = 1 } ^ { M }$

3: Measure the current state of the EV: x0;

4: Measure the current states of M nearest surrounding HVs:

$$
\left\{\mathbf {O} _ {0} ^ {(i)} \right\} _ {i = 1} ^ {M};
$$

5: Predict the final step position of the M nearest HVs:

$$
\left\{\mathbf {O} _ {N} ^ {(i)} \right\} _ {i = 1} ^ {M};
$$

6: Update the target lateral goal vector $\mathbf { P } _ { y , g }$ using (29);

7: Update the target longitudinal goal vector $\mathbf { P } _ { x , g }$ using (30);

8: Check the safety of each goal point in the goal vector using (31);

# 9: While Unsafe do:

Decrease the corresponding unsafe longitudinal points with a constant interval $\Delta d _ { x } ;$

Check Safety using (31);

# 10: End While

11: Obtain the goal vector $[ \mathbf { P } _ { x , g } \ \mathbf { P } _ { y , g } ] ^ { T } .$

$$
\mathbf {A} _ {0} \left[ \begin{array}{l} \mathbf {C} _ {x} \\ \mathbf {C} _ {y} \end{array} \right] \in \mathcal {D} _ {0}, \mathbf {A} _ {f} \left[ \begin{array}{l} \mathbf {C} _ {x} \\ \mathbf {C} _ {y} \end{array} \right] \in \mathcal {D} _ {f}, \tag {32c}
$$

$$
\boldsymbol {\omega} \in \mathcal {C} _ {\omega}, \mathbf {d} \in \mathcal {C} _ {d}, \tag {32d}
$$

$$
\dot {\mathbf {W}} _ {B} ^ {T} \mathbf {C} _ {x} - \mathbf {V} \cdot \cos \mathbf {W} _ {B} ^ {T} \mathbf {C} _ {\theta} = 0, \tag {32e}
$$

$$
\dot {\mathbf {W}} _ {B} ^ {T} \mathbf {C} _ {y} - \mathbf {V} \cdot \sin \mathbf {W} _ {B} ^ {T} \mathbf {C} _ {\theta} = 0, \tag {32f}
$$

$$
\mathbf {V} _ {w} \mathbf {C} _ {x} - \mathbf {O} _ {x} - \mathbf {L} _ {x} \cdot \mathbf {d} \cdot \cos \omega = 0, \tag {32g}
$$

$$
\mathbf {V} _ {w} \mathbf {C} _ {y} - \mathbf {O} _ {y} - \mathbf {L} _ {y} \cdot \mathbf {d} \cdot \sin \omega = 0, \tag {32h}
$$

$$
\mathbf {G} \mathbf {C} _ {x} - \mathbf {h} _ {x} \leq 0, \tag {32i}
$$

$$
\mathbf {G} \mathbf {C} _ {y} - \mathbf {h} _ {y} \leq 0. \tag {32j}
$$

Here, the variable $\mathbf { C } _ { \theta } ~ \in ~ \mathbb { R } ^ { ( n + 1 ) \times N _ { c } }$ with $[ \mathbf { C } _ { \theta } ] _ { i , j } ~ = ~ c _ { \theta , i } ^ { ( j ) }$ c θ ,i ; $\mathbf { C } _ { x } \in \mathbb { R } ^ { ( n + 1 ) \times N _ { c } }$ with $[ \mathbf { C } _ { x } ] _ { i , j } = c _ { x , i } ^ { ( j ) } ; \mathbf { C } _ { y } \in \mathbb { R } ^ { ( n + 1 ) \times N _ { c } }$ with $[ \mathbf { C } _ { y } ] _ { i , j } = c _ { y , i } ^ { ( j ) }$ . The variable $\pmb { \omega } = [ \pmb { \omega } _ { 0 } \quad \pmb { \omega } _ { 1 } \quad \ldots \quad \pmb { \omega } _ { N c - 1 } ] \in$ $\mathbb { R } ^ { ( N \times M ) \times N _ { c } }$ , where each $\omega _ { j } \in \mathbb { R } ^ { N \times M }$ corresponds to a matrix vertically stacking relative angle $\omega _ { k } ^ { ( i ) }$ , $\forall k \in \bar { \mathcal { T } } _ { 0 } ^ { N - 1 } , i \in \mathcal { T } _ { 0 } ^ { M - 1 }$ , considering M surrounding interactive HVs at N planning time steps. The variable $\mathbf { d } \ = \ [ \mathbf { d } _ { 0 } \mathbf { d } _ { 1 } \dots \mathbf { d } _ { N c - 1 } ] \in$ $\mathbb { R } ^ { ( N \times M ) \times N _ { c } }$ has a similar structure, with each $\mathbf { d } _ { j } \in \mathbb { R } ^ { N \times M }$ constructed by vertically stacking $d _ { k } ^ { ( i ) } , \forall k \in \mathcal { T } _ { 0 } ^ { N - 1 } , i \in \mathcal { T } _ { 0 } ^ { M - 1 }$ .

The sets $\mathcal { C } _ { 0 }$ and $\mathcal { D } _ { 0 }$ denote the initial constraints in heading angle, position, and velocity, while the sets $\mathcal { C } _ { f }$ and $\mathcal { D } _ { f }$ denote the corresponding target navigation state sets derived from $( 2 6 \mathrm { a } ) – ( 2 7 \mathrm { b } ) . \ \mathcal { C } _ { \omega }$ and $\mathcal { C } _ { d }$ in (32d) represent the value sets of the variables $d _ { k } ^ { ( i ) }$ and $\omega _ { k } ^ { ( i ) }$ , respectively. These sets are derived from the constraints specified in (12) and (14), respectively.

Note that matrix $\begin{array} { c c c c c c c c } { \mathbf { V } } & { = } & { [ \mathbf { V } _ { 0 } } & { \mathbf { V } _ { 1 } } & { \dots } & { \mathbf { V } _ { N c - 1 } ] } & { \in } \end{array}$ $\mathbb { R } ^ { N \times N _ { c } }$ , where each element V represents the vertical stacking of $v _ { k } ^ { ( j ) }$ for all $k ~ \in ~ \mathcal { T } _ { 0 } ^ { N - 1 }$ based on its closedform solution (25). The constant matrices $\mathbf { L } _ { x }$ and $\mathbf { L } _ { y }$ are defined as $\mathbf L _ { x } ~ = ~ [ \mathbf L _ { x , 0 } ~ \mathbf L _ { x , 1 } ~ . . . ~ \mathbf L _ { x , N c - 1 } ] ~ \mathrm { a n d } ~ \mathbf L _ { y }$ $\begin{array} { r l } { \mathbf { L } _ { \boldsymbol { \Psi } } } & { { } = } \end{array}$ $[ \mathbf { L } _ { y , 0 } \quad \mathbf { L } _ { y , 1 } \quad \dots \quad \mathbf { L } _ { y , N c - 1 } ]$ , both belonging to $\mathbb { R } ^ { ( N \times M ) \times N _ { c } }$ . Each element of these matrices is constructed by stacking $l _ { x } ^ { ( i ) }$ and $l _ { y } ^ { ( i ) }$ for N planning time steps, $\forall i \in \mathcal { T } _ { 0 } ^ { M - 1 }$ .

The predicted longitudinal and lateral positions of M surrounding HVs in N planning time steps for $N _ { c }$ freeend homotopic candidate trajectories are denoted by $\mathbf { 0 } _ { x } \in$ $\mathbb { R } ^ { ( N \times M ) \times N _ { c } }$ and $\mathbf { O } _ { v } \in \mathbb { R } ^ { ( N \times \check { M } ) \times N _ { c } }$ , respectively. Additionally, the constant matrix $\mathbf { V } _ { w } ~ = ~ \mathbf { W } _ { R } ^ { T } \otimes \mathbf { \bar { I } } _ { M } ~ \in ~ \mathbf { \bar { \mathbb { R } } } ^ { } ( N \times M ) \times ( n + \mathbf { \bar { I } } )$ represents the vertical stacking of $\bar { \mathbf { W } } _ { B } ^ { T }$ for M surrounding HVs.

In the objective function (32a), $f ( \mathbf { C } _ { \theta } ) , f ( \mathbf { C } _ { x } )$ , and $f ( \mathbf { C } _ { y } )$ are in the quadratic form:

$$
f (\mathbf {C} _ {\theta}) = \frac {1}{2} \mathbf {C} _ {\theta} ^ {T} Q _ {\theta} \mathbf {C} _ {\theta}, \tag {33}
$$

$$
f (\mathbf {C} _ {x}) = \frac {1}{2} \mathbf {C} _ {x} ^ {T} Q _ {x} \mathbf {C} _ {x}, \tag {34}
$$

$$
f (\mathbf {C} _ {y}) = \frac {1}{2} \mathbf {C} _ {y} ^ {T} Q _ {y} \mathbf {C} _ {y}, \tag {35}
$$

where ${ \bf Q } _ { \theta } , { \bf Q } _ { x } , { \bf Q } _ { v } \in \mathbb { R } ^ { ( n + 1 ) \times ( n + 1 ) }$ are positive definite weighting matrices to penalize high-order derivatives of the generated trajectory (5), facilitating smoothness in the optimization process.

The matrices $\mathbf { F } _ { 0 } , \mathbf { F } _ { f } , \mathbf { A } _ { 0 } ,$ , and $\mathbf { A } _ { f }$ in (32c) and (32d) are constant matrices enforcing initial constraints and facilitating the EV in reaching its local target state when planning:

$$
\mathbf {F} _ {0} = \mathbf {A} _ {0} = \left[ \begin{array}{c c c c} B _ {0, n} (\delta t) & B _ {1, n} (\delta t) & \ldots & B _ {n, n} (\delta t) \\ \dot {B} _ {0, n} (\delta t) & \dot {B} _ {1, n} (\delta t) & \ldots & \dot {B} _ {n, n} (\delta t) \end{array} \right] \in \mathbb {R} ^ {2 \times (n + 1)},
$$

$$
\mathbf {F} _ {f} = \left[ \begin{array}{l l l l} B _ {0, n} (N \delta t) & B _ {1, n} (N \delta t) & \ldots & B _ {n, n} (N \delta t) \\ \dot {B} _ {0, n} (N \delta t) & \dot {B} _ {1, n} (N \delta t) & \ldots & \dot {B} _ {n, n} (N \delta t) \end{array} \right] \in \mathbb {R} ^ {2 \times (n + 1)},
$$

$$
\mathbf {A} _ {f} = \left[ B _ {0, n} (\delta t) B _ {1, n} (\delta t) \dots B _ {n, n} (\delta t) \right] \in \mathbb {R} ^ {1 \times (n + 1)}.
$$

Also, matrices $\mathbf { G } \in \mathbb { R } ^ { 6 N \times ( n + 1 ) } , \ \mathbf { h } _ { x } \ \in \ \mathbb { R } ^ { 6 N \times N _ { c } }$ , and ${ \bf h } _ { y } \in { \bf \Xi }$ $\mathbb { R } ^ { 6 N \times N _ { c } }$ are defined as follows:

$$
\mathbf {G} = \left[ \begin{array}{c c c c c} \mathbf {W} _ {B} ^ {T} & - \mathbf {W} _ {B} ^ {T} & \ddot {\mathbf {W}} _ {B} ^ {T} & - \ddot {\mathbf {W}} _ {B} ^ {T} & \dddot {\mathbf {W}} _ {B} ^ {T} \\ & & & & - \dddot {\mathbf {W}} _ {B} ^ {T} \end{array} \right] ^ {T},
$$

$$
\mathbf {h} _ {x} = \left[ \begin{array}{c c c c c} \mathbf {P} _ {x, \max} & - \mathbf {P} _ {x, \min} & \mathbf {A} _ {x, \max} & - \mathbf {A} _ {x, \min} & \mathbf {J} _ {x, \max} & - \mathbf {J} _ {x, \min} \end{array} \right] ^ {T},
$$

$$
\mathbf {h} _ {y} = \left[ \begin{array}{c c c c c} \mathbf {P} _ {y, \max} & - \mathbf {P} _ {y, \min} & \mathbf {A} _ {y, \max} & - \mathbf {A} _ {y, \min} & \mathbf {J} _ {y, \max} & - \mathbf {J} _ {y, \min} \end{array} \right] ^ {T},
$$

where matrices $\mathbf { P } _ { x , \mathrm { m a x } } , \mathbf { P } _ { x , \mathrm { m i n } } , \mathbf { P } _ { y , \mathrm { m a x } } , \mathbf { P } _ { y , \mathrm { m i n } } , \mathbf { A } _ { x , \mathrm { m a x } } , \mathbf { A } _ { x }$ ,min, $\mathbf { A } _ { y , \operatorname* { m a x } } , ~ \mathbf { A } _ { y }$ ,min, Jx,max, Jx,min, Jy,max, Jy,min $\mathbf { \Psi } \in \mathbb { R } ^ { N \times N _ { c } }$ are defined with elements as follows:

$$
\mathbf {P} _ {x, \max} [ k, j ] = p _ {x, \max}, \quad \mathbf {P} _ {x, \min} [ k, j ] = p _ {x, \min},
$$

$$
\mathbf {P} _ {y, \max} [ k, j ] = p _ {y, \max}, \quad \mathbf {P} _ {y, \min} [ k, j ] = p _ {y, \min},
$$

$$
\mathbf {A} _ {x, \max} [ k, j ] = a _ {x, \max}, \quad \mathbf {A} _ {x, \min} [ k, j ] = a _ {x, \min},
$$

$$
\mathbf {A} _ {y, \max} [ k, j ] = a _ {y, \max}, \quad \mathbf {A} _ {y, \min} [ k, j ] = a _ {y, \min},
$$

$$
\mathbf {J} _ {x, \max} [ k, j ] = j _ {x, \max}, \quad \mathbf {J} _ {x, \min} [ k, j ] = j _ {x, \min},
$$

$$
\mathbf {J} _ {y, \max} [ k, j ] = j _ {y, \max}, \quad \mathbf {J} _ {y, \min} [ k, j ] = j _ {y, \min}.
$$

Note that the road boundaries for different driving tasks are enforced by the maximum and minimum lateral position $p _ { y , \mathrm { m a x } }$ and $p _ { y , \mathrm { m i n } }$ for safety considerations. In the case of emergency driving scenarios, such as encountering road construction, the values of $p _ { y , \mathrm { m i n } }$ and $p _ { y , \mathrm { m a x } }$ can be dynamically adjusted online to accommodate this cluttered scenario.

Remark 5: As elaborated in [50], the spatiotemporal safety constraint (13) exhibits bi-convexity with respect to $\begin{array} { r l } { \dot { [ p _ { x , k } } } & { { } p _ { y , k } \quad d _ { k } ^ { ( i ) } ] ^ { T } } \end{array}$ and $[ \cos ( \omega _ { k } ^ { ( i ) } )$ C sin(ω(i )k )]T . Hence, the joint constraints $( 3 2 g )$ and $( 3 2 h )$ exhibit bi-convexity, which facilitates the decomposition into two subconstraints during optimization. One optimizes $[ \mathbf { C } _ { x } \quad \mathbf { C } _ { y } ] ^ { T }$ and d over fixed $\omega ,$ while the other optimizes ω over fixed $[ \mathbf { C } _ { x } \quad \mathbf { C } _ { y } \quad \mathbf { d } ] ^ { T }$ . Similarly, in addressing the joint constraints (32e) and (32f), one optimizes $[ \mathbf { C } _ { x } \quad \mathbf { C } _ { y } ] ^ { T }$ over a fixed $\mathbf { C } _ { \theta }$ , while the other optimizes $\mathbf { C } _ { \theta }$ over fixed $[ \dot { \mathbf { C } } _ { x } \quad \mathbf { C } _ { y } ] ^ { T }$ . The inherent convexity of the objective function (32a), characterized by individual quadratic terms (33), (34), and (35), coupled with the separable nature of the constraints, facilitates its decomposition into distinct subproblems. This separability allows us to efficiently leverage parallel optimization strategies to divide the bi-convex optimization problem (32) into parallel $Q P$ subproblems.

# B. Over-Relaxed ADMM

In this study, we solve this bi-convex optimization problem (32) using the over-relaxed ADMM by introducing slack vectors $\mathbf { Z } _ { x }$ and $\mathbf { Z } _ { \boldsymbol { y } } .$ , and applying an infinite penalty to their negative components. Each iteration includes solving smaller convex subproblems, and the associated dual variables are updated in parallel to accelerate the computation speed. To decompose this optimization problem (32) using ADMM, we introduce the definition of the indicator function.

Definition 4: The indicator function with respect to a set $\mathbb { S }$ is defined as

$$
\mathcal {I} _ {\mathbb {S}} (S) = \left\{ \begin{array}{l l} 0 & \text {   if   } S \in \mathbb {S}, \\ \infty & \text {   if   } S \notin \mathbb {S}. \end{array} \right. \tag {36}
$$

In particular, the associated augmented Lagrangian of (32) can be formulated as follows:

$$
\begin{array}{l} \mathcal {L} \left(\mathbf {C} _ {\theta}, \mathbf {C} x, \mathbf {C} _ {y}, \boldsymbol {\omega}, \mathbf {d}, \mathbf {Z} _ {x}, \mathbf {Z} _ {y}, \lambda_ {\theta}, \lambda_ {x}, \lambda_ {y}, \lambda_ {\text { obs }, x}, \lambda_ {\text { obs }, y}\right) \\ = f \left(\mathbf {C} _ {\theta}\right) + g _ {x} \left(\mathbf {C} _ {x}\right) + g _ {y} \left(\mathbf {C} _ {y}\right) + \mathcal {I} _ {+} \left(\mathbf {Z} _ {x}\right) + \mathcal {I} _ {+} \left(\mathbf {Z} _ {y}\right) \\ + \boldsymbol {\lambda} _ {\theta} ^ {T} \left(\dot {\mathbf {W}} _ {B} ^ {T} \mathbf {C} _ {x} - \mathbf {V} \cdot \cos \mathbf {W} _ {B} ^ {T} \mathbf {C} _ {\theta}\right) \\ + \boldsymbol {\lambda} _ {\theta} ^ {T} \left(\dot {\mathbf {W}} _ {B} ^ {T} \mathbf {C} _ {y} - \mathbf {V} \cdot \sin \mathbf {W} _ {B} ^ {T} \mathbf {C} _ {\theta}\right) \\ + \boldsymbol {\lambda} _ {\mathrm{obs}, x} ^ {T} \left(\mathbf {V} _ {w} \mathbf {C} _ {x} - \mathbf {O} _ {x} - \mathbf {L} _ {x} \cdot \mathbf {d} \cdot \cos \omega\right) \\ + \boldsymbol {\lambda} _ {\text { obs }, y} ^ {T} \left(\mathbf {V} _ {w} \mathbf {C} _ {y} - \mathbf {O} _ {y} - \mathbf {L} _ {y} \cdot \mathbf {d} \cdot \sin \omega\right) \\ + \boldsymbol {\lambda} _ {x} ^ {T} \mathbf {C} _ {x} + \boldsymbol {\lambda} _ {y} ^ {T} \mathbf {C} _ {y} \\ + \frac {\rho_ {\theta}}{2} \left\| \dot {\mathbf {W}} _ {B} ^ {T} \mathbf {C} _ {x} - \mathbf {V} \cdot \cos \mathbf {W} _ {B} ^ {T} \mathbf {C} _ {\theta} \right\| _ {2} ^ {2} \\ + \frac {\rho_ {\theta}}{2} \left\| \dot {\mathbf {W}} _ {B} ^ {T} \mathbf {C} _ {y} - \mathbf {V} \cdot \sin \mathbf {W} _ {B} ^ {T} \mathbf {C} _ {\theta} \right\| _ {2} ^ {2} \\ + \frac {\rho_ {\mathrm{obs} , x}}{2} \| \mathbf {V} _ {w} \mathbf {C} _ {x} - \mathbf {O} _ {x} - \mathbf {L} _ {x} \cdot \mathbf {d} \cdot \cos \omega \| _ {2} ^ {2} \\ + \frac {\rho_ {\mathrm{obs} , y}}{2} \left\| \mathbf {V} _ {w} \mathbf {C} _ {y} - \mathbf {O} _ {y} - \mathbf {L} _ {y} \cdot \mathbf {d} \cdot \sin \omega \right\| _ {2} ^ {2} \\ + \frac {\rho_ {x}}{2} \| \mathbf {G C} _ {x} - \mathbf {h} _ {x} + \mathbf {Z} _ {x} \| _ {2} ^ {2} \\ + \frac {\rho_ {y}}{2} \left\| \mathbf {G C} _ {y} - \mathbf {h} _ {y} + \mathbf {Z} _ {y} \right\| _ {2} ^ {2}, \tag {37} \\ \end{array}
$$

where $\begin{array} { r l r } { \lambda _ { \theta } } & { { } \in } & { \mathbb { R } ^ { N \times N _ { c } } , \lambda _ { \mathrm { o b s } , x } \quad \in \quad \mathbb { R } ^ { ( N \times M ) \times N _ { c } } , \lambda _ { \mathrm { o b s } , y } } \end{array}$ ∈ $\mathbb { R } ^ { ( N \times M ) \times \bar { N } _ { c } }$ are dual variables of the equality constraints (32e)–(32h); $\rho _ { \theta } , \rho _ { \mathrm { o b s } , x }$ , and $\rho _ { \mathrm { o b s , \it y } }$ are the corresponding l2 penalty parameters. The dual variables λx ∈ R(n+1)×Nc $\pmb { \lambda } _ { x } \in \mathbb { R } ^ { ( n + 1 ) \times N _ { c } }$ and $\lambda _ { \gamma } ^ { - } ~ \in ~ \hat { \mathbb { R } } ^ { ( n + 1 ) \times N _ { c } }$ are associated with constraints (32i) and (32j), respectively, contributing to enhanced iteration stability, as discussed in $[ 5 5 ] ; \rho _ { x }$ and $\rho _ { y }$ are the corresponding $l _ { 2 }$ penalty parameter. To facilitate optimization and get a feasibility solution, we introduce slack vectors $\mathbf { Z } _ { x }$ and $\mathbf { Z } _ { \mathrm { y } }$ to handle inequality constraints (32i) and (32j), respectively. Specifically, the indicator function ${ \mathcal { T } } _ { + } ( \mathbf { Z } _ { x } ) ~ = ~ 0$ if constraints (32i) is satisfied, and $\mathcal { T } _ { + } ( \mathbf { Z } _ { x } ) = \infty$ otherwise. Similarly, $\mathcal { T } _ { + } ( \mathbf { Z } _ { \mathrm { y } } )$ is the indicator function of the constraints in (32j). The structure of the augmented Lagrangian function (37) and the decomposed set constraints (32b)–(32d) allow us to group the primal variables into five groups $\{ \mathbf { C } _ { \theta } \} , \{ \mathbf { C } _ { x } , \mathbf { Z } _ { x } \} , \{ \mathbf { C } _ { y } , \mathbf { Z } _ { y } \}$ , {ω}, and {d} for alternating optimization in five subproblems. Finally, the associated dual variables can be updated concurrently.

1) ADMM Iteration for Equality Constraints: In the ADMM iteration, it aims at solving the following sub-problem for the primal variable $\mathbf { C } _ { \theta } \mathbf { : }$

$$
\begin{array}{l} \mathbf {C} _ {\theta} ^ {\iota + 1} = \min _ {\mathbf {C} _ {\theta}} \mathcal {L} \left(\left\{\mathbf {C} _ {\theta} \right\}, \left\{\mathbf {C} _ {x} ^ {\iota}, \mathbf {Z} _ {x} ^ {\iota} \right\}, \left\{\mathbf {C} _ {y} ^ {\iota}, \mathbf {Z} _ {y} ^ {\iota} \right\}, \left\{\boldsymbol {\omega} ^ {\iota} \right\}, \left\{\mathbf {d} ^ {\iota} \right\}, \right. \\ \left. \{\boldsymbol {\lambda} _ {\theta} ^ {\iota}, \boldsymbol {\lambda} _ {x} ^ {\iota}, \boldsymbol {\lambda} _ {y} ^ {\iota}, \boldsymbol {\lambda} _ {\mathrm{obs}, x} ^ {\iota}, \boldsymbol {\lambda} _ {\mathrm{obs}, y} ^ {\iota} \}\right) \\ = \min _ {\mathbf {C} _ {\theta}} \frac {1}{2} \mathbf {C} _ {\theta} ^ {T} Q _ {\theta} \mathbf {C} _ {\theta} + \boldsymbol {\lambda} _ {\theta} ^ {\iota T} \left\| \begin{array}{c} \dot {\mathbf {W}} _ {B} ^ {T} \mathbf {C} _ {x} ^ {\iota} - \mathbf {V} \cdot \cos \mathbf {W} _ {B} ^ {T} \mathbf {C} _ {\theta} \\ \dot {\mathbf {W}} _ {B} ^ {T} \mathbf {C} _ {y} ^ {\iota} - \mathbf {V} \cdot \sin \mathbf {W} _ {B} ^ {T} \mathbf {C} _ {\theta} \end{array} \right\| \\ + \frac {\rho_ {\theta}}{2} \left\| \begin{array}{c} \dot {\mathbf {W}} _ {B} ^ {T} \mathbf {C} _ {x} ^ {\iota} - \mathbf {V} \cdot \cos \mathbf {W} _ {B} ^ {T} \mathbf {C} _ {\theta} \\ \dot {\mathbf {W}} _ {B} ^ {T} \mathbf {C} _ {y} ^ {\iota} - \mathbf {V} \cdot \sin \mathbf {W} _ {B} ^ {T} \mathbf {C} _ {\theta} \end{array} \right\| ^ {2} \\ \text { s.t. } \quad \mathbf {F} _ {0} \mathbf {C} _ {\theta} = [ \boldsymbol {\theta} _ {0} \dot {\boldsymbol {\theta}} _ {0} ] ^ {T}, \mathbf {F} _ {f} \mathbf {C} _ {\theta} = \mathbf {0}, \tag {38} \\ \end{array}
$$

where ι denotes the current iteration number. The target set $\mathbf { C } _ { f }$ is set to a zero vector. This constraint is imposed to ensure that the final step of each trajectory exhibits a zero heading angle and yaw rate, thereby enhancing driving stability. The vectors $\pmb { \theta } _ { 0 } ~ \in ~ \mathbb { R } ^ { 1 \times N _ { c } }$ and $\dot { \pmb \theta _ { 0 } } ~ \in ~ \mathbb { R } ^ { 1 \times N _ { c } }$ are formed by horizontally stacking the initial heading angle $\theta ( 0 )$ and yaw rate $\dot { \theta } ( 0 )$ for $N _ { c }$ free-end homotopic candidate trajectories.

Leveraging the polar transformation (24), the subproblem (38) can be converted into the following constrained least squares problem:

$$
\begin{array}{l} \mathbf {C} _ {\theta} ^ {\iota + 1} = \min _ {\mathbf {C} _ {\theta}} \frac {1}{2} \mathbf {C} _ {\theta} ^ {T} Q _ {\theta} \mathbf {C} _ {\theta} \\ + \boldsymbol {\lambda} _ {\theta} ^ {t T} \left\| \mathbf {W} _ {B} ^ {T} \mathbf {C} _ {\theta} - \arctan \left(\frac {\dot {\mathbf {W}} _ {B} ^ {T} \mathbf {C} _ {y} ^ {t}}{\dot {\mathbf {W}} _ {B} ^ {T} \mathbf {C} _ {x} ^ {t}}\right) \right\| \\ + \frac {\rho_ {\theta}}{2} \left\| \mathbf {W} _ {B} ^ {T} \mathbf {C} _ {\theta} - \arctan \left(\frac {\dot {\mathbf {W}} _ {B} ^ {T} \mathbf {C} _ {y} ^ {\iota}}{\dot {\mathbf {W}} _ {B} ^ {T} \mathbf {C} _ {x} ^ {\iota}}\right) \right\| ^ {2} \\ \text { s.t. } \quad \mathbf {F} _ {0} \mathbf {C} _ {\theta} = [ \boldsymbol {\theta} _ {0} \quad \dot {\boldsymbol {\theta}} _ {0} ] ^ {T}, \mathbf {F} _ {f} \mathbf {C} _ {\theta} = \mathbf {0}. \\ \end{array}
$$

As a result, we can obtain the following analytical solutions for the variable $\mathbf { C } _ { \theta }$ :

$$
\mathbf {C} _ {\theta} = \mathbf {A} _ {\theta} ^ {\dagger} \mathbf {b} _ {\theta}, \tag {39}
$$

where ${ \bf A } _ { \theta } ^ { \dagger }$ denotes the Moore-Penrose pseudoinverse of $\mathbf { A } _ { \theta }$ ,

$$
\mathbf {A} _ {\theta} = \left[ \begin{array}{c} \mathbf {Q} _ {\theta} + \rho_ {\theta} \mathbf {W} _ {B} \mathbf {W} _ {B} ^ {T} \\ \mathbf {F} _ {0} \\ \mathbf {F} _ {f} \end{array} \right],
$$

$$
\mathbf {b} _ {\theta} = \left[ \begin{array}{c} - \mathbf {W} _ {B} \boldsymbol {\lambda} _ {\theta} + \rho_ {\theta} \mathbf {W} _ {B} \arctan \left(\frac {\dot {\mathbf {W}} _ {B} ^ {T} \mathbf {C} _ {y} ^ {\iota}}{\dot {\mathbf {W}} _ {B} ^ {T} \mathbf {C} _ {x} ^ {\iota}}\right) \\ [ \boldsymbol {\theta} _ {0} \quad \dot {\boldsymbol {\theta}} _ {0} ] ^ {T} \\ \mathbf {0} \end{array} \right].
$$

2) Over-Relaxed ADMM Iterations for Inequality Constraints: We aim at solving the following constrained least squares problem for the variable $\{ \mathbf { C } _ { x } , \mathbf { Z } _ { x } \}$ based on the over-relaxed ADMM iteration:

$$
\begin{array}{l} \mathbf {C} _ {x} ^ {\iota + 1} = \min _ {\mathbf {C} _ {x}} \mathcal {L} \Big (\{\mathbf {C} _ {\theta} ^ {\iota} \}, \{\mathbf {C} _ {x}, \mathbf {Z} _ {x} ^ {\iota} \}, \{\mathbf {C} _ {y} ^ {\iota}, \mathbf {Z} _ {y} ^ {\iota} \}, \{\boldsymbol {\omega} ^ {\iota} \}, \{\mathbf {d} ^ {\iota} \}, \\ \left. \{\pmb {\lambda} _ {\theta} ^ {\iota}, \pmb {\lambda} _ {x} ^ {\iota}, \pmb {\lambda} _ {y} ^ {\iota}, \pmb {\lambda} _ {\mathrm{obs}, x} ^ {\iota}, \pmb {\lambda} _ {\mathrm{obs}, y} ^ {\iota} \}\right) \\ = \min _ {\mathbf {C} _ {x}} \frac {1}{2} \mathbf {C} _ {x} ^ {T} Q _ {x} \mathbf {C} _ {x} + \lambda_ {x} ^ {\iota T} \mathbf {C} _ {x} \\ + \boldsymbol {\lambda} _ {\theta} ^ {\iota T} \left(\dot {\mathbf {W}} _ {B} ^ {T} \mathbf {C} _ {x} - \mathbf {V} \cdot \cos \mathbf {W} _ {B} ^ {T} \mathbf {C} _ {\theta} ^ {\iota}\right) \\ + \boldsymbol {\lambda} _ {\text { obs }, x} ^ {\iota T} \left(\mathbf {V} _ {w} \mathbf {C} _ {x} - \mathbf {O} _ {x} - \mathbf {L} _ {x} \cdot \mathbf {d} ^ {\iota} \cdot \cos \omega^ {\iota}\right) \\ + \frac {\rho_ {\theta}}{2} \left\| \dot {\mathbf {W}} _ {B} ^ {T} \mathbf {C} _ {x} - \mathbf {V} \cdot \cos \mathbf {W} _ {B} ^ {T} \mathbf {C} _ {\theta} ^ {\iota} \right\| _ {2} ^ {2} \\ + \frac {\rho_ {\mathrm{obs} , x}}{2} \left\| \mathbf {V} _ {w} \mathbf {C} _ {x} - \mathbf {O} _ {x} - \mathbf {L} _ {x} \cdot \mathbf {d} ^ {\iota} \cdot \cos \omega^ {\iota} \right\| _ {2} ^ {2} \\ + \frac {\rho_ {x}}{2} \left\| \mathbf {G C} _ {x} - \mathbf {h} _ {x} + \mathbf {Z} _ {x} ^ {\iota} \right\| _ {2} ^ {2} \\ \mathrm{s.t.} \quad \mathbf {A} _ {0} \mathbf {C} _ {x} = [ \mathbf {P} _ {x, 0} \quad \mathbf {V} _ {x, 0} ] ^ {T}, \mathbf {A} _ {f} \mathbf {C} _ {x} = \mathbf {P} _ {x, g}, \\ \end{array}
$$

where the vectors $\mathbf { P } _ { x , 0 } \in \mathbb { R } ^ { 1 \times N _ { c } }$ and $\mathbf { V } _ { x , 0 } \in \mathbb { R } ^ { 1 \times N _ { c } }$ are formed by horizontally stacking the initial longitudinal position $p _ { x , 0 }$ and longitudinal velocity $v _ { x , 0 }$ for $N _ { c }$ free-end homotopic candidate trajectories. As a result, we can get the following analytical solutions for the variable $\mathbf { C } _ { x }$ :

$$
\mathbf {C} _ {x} ^ {\iota + 1} = \mathbf {A} _ {x} ^ {\dagger} \mathbf {b} _ {x}, \tag {40}
$$

where $\mathbf { A } _ { x } ^ { \dagger }$ denotes the Moore-Penrose pseudoinverse of $\mathbf { A } _ { x } .$ ,

$$
\mathbf {A} _ {x} = \left[ \begin{array}{c} \mathbf {Q} _ {x} + \rho_ {\theta} \dot {\mathbf {W}} _ {B} \dot {\mathbf {W}} _ {B} ^ {T} + \rho_ {\mathrm{obs}, x} \mathbf {V} _ {w} ^ {T} \mathbf {V} _ {w} + \rho_ {x} \mathbf {G} ^ {T} \mathbf {G} \\ \mathbf {A} _ {0} \\ \mathbf {A} _ {f} \end{array} \right],
$$

$$
\mathbf {b} _ {x} = \left[ \begin{array}{c} \mathbf {b} _ {x, 1} \\ [ \mathbf {P} _ {x, 0} \quad \mathbf {V} _ {x, 0} ] ^ {T} \\ \mathbf {P} _ {x, g} \end{array} \right],
$$

and $\mathbf { b } _ { x , 1 }$ is given by

$$
\begin{array}{l} \mathbf {b} _ {x, 1} = - \boldsymbol {\lambda} _ {x} ^ {\iota} - \dot {\mathbf {W}} _ {B} \boldsymbol {\lambda} _ {\theta} ^ {\iota} - \mathbf {V} _ {w} ^ {T} \boldsymbol {\lambda} _ {\text { obs }, x} ^ {\iota} \\ + \rho_ {\theta} \dot {\mathbf {W}} _ {B} \mathbf {V} \cdot \cos \mathbf {W} _ {B} ^ {T} \mathbf {C} _ {\theta} ^ {\iota} \\ + \rho_ {\text { obs }, x} \mathbf {V} _ {w} ^ {T} (\mathbf {O} _ {x} + \mathbf {L} _ {x} \cdot \mathbf {d} ^ {\iota} \cdot \cos \omega^ {\iota}) \\ + \frac {\rho_ {x}}{2} \mathbf {G} ^ {T} (\mathbf {h} _ {x} - \mathbf {Z} _ {x} ^ {\iota}). \\ \end{array}
$$

The corresponding slack variable vector $\mathbf { Z } _ { x }$ , which facilitates optimization and guarantees solving feasibility, is updated as follows:

$$
\mathbf {Z} _ {x} ^ {\iota + 1} = \max \Big (\mathbf {0}, \min _ {\mathbf {Z} _ {x}} \mathcal {L} \Big (\{\mathbf {C} _ {\theta} ^ {\iota + 1} \}, \{\mathbf {Z} _ {x}, \mathbf {C} _ {x} ^ {\iota + 1} \}, \{\mathbf {C} _ {y} ^ {\iota}, \mathbf {Z} _ {y} ^ {\iota} \},
$$

$$
\begin{array}{l} \left. \{\boldsymbol {\omega} ^ {l} \}, \{\mathbf {d} ^ {l} \}, \{\lambda_ {\theta} ^ {l}, \lambda_ {x} ^ {l}, \lambda_ {y} ^ {l}, \lambda_ {\mathrm{obs}, x} ^ {l}, \lambda_ {\mathrm{obs}, y} ^ {l} \}\right)\left. \right), \\ = \max \left(\mathbf {0}, \mathbf {h} _ {x} - \mathbf {G C} _ {x} ^ {\iota + 1}\right), \tag {41} \\ \end{array}
$$

which leads to the corresponding dual variable $\lambda _ { x }$ update:

$$
\boldsymbol {\lambda} _ {x} ^ {\iota + 1} = \boldsymbol {\lambda} _ {x} ^ {\iota} + \rho_ {x} (\mathbf {G C} _ {x} ^ {\iota + 1} - \mathbf {h} _ {x} + \mathbf {Z} _ {x} ^ {\iota + 1}). \tag {42}
$$

To improve the convergence properties of the algorithm, one must also account for past iterations when computing the next ones. Consider the relaxation of (41) and (42) obtained by replacing $\mathbf { G C } _ { x } ^ { \iota + 1 }$ in $\mathbf { Z } _ { x }$ the $\lambda _ { x }$ -updates with $\alpha { \bf G } { \bf C } _ { x } ^ { \imath + 1 } - ( 1 -$ $\alpha ) ( { \bf Z } _ { x } ^ { \iota } - { \bf h } _ { x } )$ . The resulting iterations take the form:

$$
\mathbf {Z} _ {x} ^ {\iota + 1} = \max \left(\mathbf {0}, \mathbf {h} _ {x} - \mathbf {G C} _ {x} ^ {\iota + 1}\right), \tag {43a}
$$

$$
\boldsymbol {\lambda} _ {x} ^ {\iota + 1} = \boldsymbol {\lambda} _ {x} ^ {\iota} + \rho_ {x} (\alpha_ {x} (\mathbf {G C} _ {x} ^ {\iota + 1} - \mathbf {h} _ {x} + \mathbf {Z} _ {x} ^ {\iota + 1})
$$

$$
+ (1 - \alpha_ {x}) (\mathbf {Z} _ {x} ^ {\iota + 1} - \mathbf {Z} _ {x} ^ {\iota})). \tag {43b}
$$

Similarly, the following iteration results for variable $\mathbf { C } _ { y }$ based on the over-relaxed ADMM iteration are obtained:

$$
\mathbf {C} _ {y} ^ {\iota + 1} = \mathbf {A} _ {y} ^ {\dagger} \mathbf {b} _ {y}, \tag {44}
$$

where ${ \bf A } _ { y } ^ { \dagger }$ denotes the Moore-Penrose pseudoinverse of $\mathbf { A } _ { y }$

$$
\begin{array}{l} \mathbf {A} _ {y} = \left[ \begin{array}{c} \mathbf {Q} _ {y} + \rho_ {\theta} \dot {\mathbf {W}} _ {B} \dot {\mathbf {W}} _ {B} ^ {T} + \rho_ {\mathrm{obs}, y} \mathbf {V} _ {w} ^ {T} \mathbf {V} _ {w} + \rho_ {y} \mathbf {G} ^ {T} \mathbf {G} \\ \mathbf {A} _ {0} \\ \mathbf {A} _ {f} \end{array} \right], \\ \mathbf {b} _ {y} = \left[ \begin{array}{c} \mathbf {b} _ {y, 1} \\ [ \mathbf {P} _ {y, 0} \quad \mathbf {V} _ {y, 0} ] ^ {T} \\ \mathbf {P} _ {y, g} \end{array} \right]. \\ \end{array}
$$

Here, the vectors $\mathbf { P } _ { y , 0 } \in \mathbb { R } ^ { 1 \times N _ { c } }$ and ${ \bf V } _ { y , 0 } \in \mathbb { R } ^ { 1 \times N _ { c } }$ are formed by horizontally stacking the initial lateral position $p _ { y , 0 }$ and lateral velocity $v _ { y , 0 }$ for $N _ { c }$ homotopic candidate trajectories. The term ${ \bf b } _ { y , 1 }$ is defined as:

$$
\begin{array}{l} \mathbf {b} _ {y, 1} = - \boldsymbol {\lambda} _ {y} ^ {\iota} - \dot {\mathbf {W}} _ {B} \boldsymbol {\lambda} _ {\theta} ^ {\iota} - \mathbf {V} _ {w} ^ {T} \boldsymbol {\lambda} _ {\text { obs }, y} ^ {\iota} \\ + \rho_ {\theta} \dot {\mathbf {W}} _ {B} \mathbf {V} \cdot \sin \mathbf {W} _ {B} ^ {T} \mathbf {C} _ {\theta} ^ {\iota} \\ + \rho_ {\mathrm{obs}, y} \mathbf {V} _ {w} ^ {T} (\mathbf {O} _ {y} + \mathbf {L} _ {y} \cdot \mathbf {d} ^ {\iota} \cdot \sin \omega^ {\iota}) \\ + \frac {\rho_ {y}}{2} \mathbf {G} ^ {T} (\mathbf {h} _ {y} - \mathbf {Z} _ {y} ^ {\iota}). \\ \end{array}
$$

The updates for the associated slack variable $\mathbf { Z } _ { y }$ and dual variable $\lambda _ { y }$ are as follows:

$$
\mathbf {Z} _ {y} ^ {\iota + 1} = \max \left(\mathbf {0}, \mathbf {h} _ {y} - \mathbf {G C} _ {y} ^ {\iota + 1}\right), \tag {45a}
$$

$$
\boldsymbol {\lambda} _ {y} ^ {\iota + 1} = \boldsymbol {\lambda} _ {y} ^ {\iota} + \rho_ {y} (\alpha_ {y} (\mathbf {G C} _ {y} ^ {\iota + 1} - \mathbf {h} _ {y} + \mathbf {Z} _ {y} ^ {\iota + 1})
$$

$$
+ (1 - \alpha_ {y}) (\mathbf {Z} _ {y} ^ {\iota + 1} - \mathbf {Z} _ {y} ^ {\iota})). \tag {45b}
$$

Note that the relaxation parameters $\alpha _ { x }$ and $\alpha _ { y }$ are recommended to be within the range [1.5, 1.8], as detailed in [13] and [56]. In this study, we choose 1.5 as the iteration coefficient for both $\alpha _ { x }$ and $\alpha _ { y }$ .

3) ADMM Iterations for Variables ω and d: Referring to [51] and considering the constraints in (12) and (14), the updated iterates for ω and d can be expressed as follows:

$$
\mathbf {d} ^ {\iota + 1} = \max \left(\mathbf {0}, 1 + (1 - \alpha_ {k}) \cdot (\mathbf {d} ^ {\iota} - 1))\right), \tag {46}
$$

$$
\boldsymbol {\omega} ^ {\iota + 1} = \arctan \left(\frac {\mathbf {L} _ {x} \cdot \left(\mathbf {V} _ {w} \mathbf {C} _ {y} ^ {\iota + 1} - \mathbf {O} _ {y}\right)}{\mathbf {L} _ {y} \cdot \left(\mathbf {V} _ {w} \mathbf {C} _ {x} ^ {\iota + 1} - \mathbf {O} _ {x}\right)}\right), \tag {47}
$$

where the augmented barrier coefficient matrix $\alpha _ { k } \in$ $\mathbb { R } ^ { ( N \times M ) \times N _ { c } }$ and each element lies within the interval $( 0 , 1 )$ . This parameter represents the aggressiveness of collision avoidance maneuvers and safety recovery as elaborated in Section III-B.

Remark 6: The update rule (46) ensures that each element of the matrix d remains positive, thus adhering to safety constraints during iterations.

4) Dual Update:

$$
\boldsymbol {\lambda} _ {\theta} ^ {\iota + 1} = \boldsymbol {\lambda} _ {\theta} ^ {\iota} + \rho_ {\theta} \left\| \mathbf {W} _ {B} ^ {T} \mathbf {C} _ {\theta} ^ {\iota + 1} - \arctan \left(\frac {\dot {\mathbf {W}} _ {B} ^ {T} \mathbf {C} _ {y} ^ {\iota + 1}}{\dot {\mathbf {W}} _ {B} ^ {T} \mathbf {C} _ {x} ^ {\iota + 1}}\right) \right\|, \tag {48}
$$

$$
\begin{array}{l} \boldsymbol {\lambda} _ {\mathrm{obs}, x} ^ {\iota + 1} = \boldsymbol {\lambda} _ {\mathrm{obs}, x} ^ {\iota} + \rho_ {\mathrm{obs}, x} \left(\mathbf {V} _ {w} \mathbf {C} _ {x} ^ {\iota + 1} - \mathbf {O} _ {x} \right. \\ \left. - \mathbf {L} _ {x} \cdot \mathbf {d} ^ {\iota + 1} \cdot \cos \omega^ {\iota + 1}\right), \tag {49} \\ \end{array}
$$

$$
\boldsymbol {\lambda} _ {\mathrm{obs}, y} ^ {\iota + 1} = \boldsymbol {\lambda} _ {\mathrm{obs}, y} ^ {\iota} + \rho_ {\mathrm{obs}, y} \left(\mathbf {V} _ {w} \mathbf {C} _ {y} ^ {\iota + 1} - \mathbf {O} _ {y} \right.
$$

$$
\left. - \mathbf {L} _ {y} \cdot \mathbf {d} ^ {\iota + 1} \cdot \sin \omega^ {\iota + 1}\right). \tag {50}
$$

Detailed procedure of the BPHTO approach is provided in Algorithm 2.

# C. Candidate Trajectories Evaluation and Selection

In this study, the evaluation algorithm is designed to evaluate all free-end homotopic candidate trajectories obtained in Section V, then the optimal trajectory $\xi ^ { * }$ aligning with the optimal maneuver $\tau ^ { * }$ selected for the EV to execute as follows:

$$
s (\xi_ {j}, \tau_ {j}) = \mathbf {w} ^ {T} \mathbf {f} (\xi_ {j}, \tau_ {j}), \tag {51}
$$

$$
\{\xi^ {*}, \tau^ {*} \} = \min _ {\xi_ {j} \in \Xi , \tau_ {j} \in \mathcal {T}} s (\xi_ {j}, \tau_ {j}), \tag {52}
$$

where $s ( \xi , \tau )$ is the overall evaluation cost function. The weight vector $\mathbf { w } = [ w _ { g } \quad w _ { l } \quad w _ { s } \quad w _ { c } \quad w _ { m } ] ^ { T }$ indicates the relative significance of each sub-cost for a trajectory. Concurrently, the vector $\mathbf { f } ( \xi _ { j } , \tau _ { j } )$ denotes a vector of sub-costs that captures various aspects of the j -th trajectory’s performance as follows:

$$
\mathbf {f} (\xi_ {j}, \tau_ {j}) = [ F _ {g} \quad F _ {l} \quad F _ {s} \quad F _ {c} \quad F _ {m} ] ^ {T},
$$

where $F _ { g } , F _ { l } , F _ { s } , F _ { c } ,$ and $F _ { m }$ represent the goal-tracking, lateral deviation, safety, comfort, and consistency costs, respectively. For a cruise driving task, $F _ { g }$ measures the gap between the actual velocity of the EV and the target cruise velocity $v _ { g } .$ . The lateral deviation cost $F _ { l }$ is computed from the deviation of the target lane of each candidate trajectory and the generated trajectory. The safety cost $F _ { s }$ is measured by the primal residual of safety in updating dual variables $\lambda _ { \mathrm { o b s } , x }$ (49) and $\lambda _ { \mathrm { o b s , } y }$ (50). The comfort cost $F _ { c }$ is obtained from the average jerk value of each candidate trajectory. Besides, we leverage a decaying strategy with respect to planning steps in a horizon for $F _ { g } , F _ { l } ,$ , and $F _ { c }$ based on our previous work [28]. To enhance driving consistency, the latest selected trajectory is given precedence. Therefore, the consistency cost is measured by the target driving lane changing between two consecutive decision-making instants, as detailed in [28].

Algorithm 2 BPHTO With ADMM   
1: Parameters: f: Nonlinear Dubin's car model [43]; $Q_{\theta}, Q_{x}, Q_{y}$ : Weights in the cost function; $\rho_{\theta}, \rho_{x}, \rho_{y}, \rho_{obs,x}, \rho_{obs,y}: l_{2}$ penalty weights; $N_{c}$ : Number of the candidate trajectories;
N: Planning horizon; $K_{max}$ : Number of the maximum iterations;
m: Dimension of Bézier curves;
n: Order of Bézier curves; $\alpha_{k}$ : Barrier coefficient matrix; $L_{x}, L_{y}$ : Stack matrices for safe ellipse: $\epsilon^{pri}$ : Stopping criterion value of iteration; $r_{l}$ : Lateral perception range of the EV;
M: Number of the anticipated HVs;
2: Initialize the states of the M nearest HVs: $\left\{O_{0}^{(i)}\right\}_{i=1}^{M}$ ;
3: Initialize the nominal control point matrices $W_{P,j}$ ;
4: Obtain the local target navigation $[P_{x,g} P_{y,g}]^{T}$ from Algorithm 1;
5: While task is not done do:
6: Measure the current state of the EV: $x_{0}$ ;
7: Measure the current states of M nearest surrounding HVs: $\left\{O_{0}^{(i)}\right\}_{i=1}^{M}$ within lateral perception range $r_{l}$ ;
8: Predict the future trajectories of the M nearest HVs: $\left\{O_{k}^{(i)}\right\}_{k=1}^{N}$ , $i = 1, 2, \cdots, M$ ;
9: For $\iota \leftarrow 0$ to $K_{max}$ do:
10: Update the primal variable $C_{\theta}^{\iota+1} (39)$ ;
11: Update the primal variable $C_{x}^{\iota+1} (40)$ ;
12: Update the slack vector $Z_{x}^{\iota+1}(43a)$ ;
13: Update the primal variables $C_{y}^{\iota+1} (44)$ ;
14: Update the slack vector $Z_{y}^{\iota+1} (45a)$ ;
15: Update the primal variables $d^{\iota+1} (46)$ and $\omega^{\iota+1} (47)$ ;
16: Update the dual variables $\lambda_{\theta}^{\iota+1} (48), \lambda_{x}^{\iota+1} (43b), \lambda_{y}^{\iota+1} (45b), \lambda_{obs,x}^{\iota+1} (49), \text{and } \lambda_{obs,y}^{\iota+1} (50)$ ;
17: Break if the primal residual less than $\epsilon^{pri}$ ;
18: End For
19: Get optimized control point matrices $W_{P,j}$ and trajectories $\left\{C_{k}^{(j)}, \dot{C}_{k}^{(j)}, \ddot{C}_{k}^{(j)}\right\}_{k=0}^{N-1}, j \in I_{0}^{N_{c}-1}$ ;
20: Evaluate each candidate trajectory sequence (51);
21: Select the optimal trajectory sequence $\left\{C_{k}^{(j*)}, \dot{C}_{k}^{(j*)}, \ddot{C}_{k}^{(j*)}\right\}_{k=0}^{N-1} (52)$ ;
22: Send the first step of the optimal trajectory to the EV;
23: Reinitialize nominal control point matrices $\{\bar{x}_{k+1}, \bar{u}_{k}\}_{k=0}^{N-2} \leftarrow \{x_{k+1}, u_{k}\}_{k=1}^{N-1}$ .
24: End While

# VI. EXPERIMENTAL RESULTS

In this section, we validate the effectiveness of the proposed BPHTO approach under various cluttered static and dynamic scenarios with uncertain HVs with synthetic IDM and realworld datasets. Our experiments were implemented in C++ and Robot Operating System 2 on an Ubuntu 22.04 system with an AMD Ryzen 5 5600G CPU with six cores @3.90 GHz and 16 GB RAM. The frequency of the processor is at a base clock speed of 2.28 GHz, with a maximum boost frequency of 3.20 GHz and a minimum frequency of 1.20 GHz.

# A. Experimental Setup

1) Dataset: The efficacy of the proposed BPHTO method in safety-critical driving scenarios is compared with other stateof-the-art baselines under various tasks. We leverage both synthetic IDM and real-world datasets obtained from the Next Generation Simulation (NGSIM) project1 in our experiments. The NGSIM dataset was collected from the I-80 freeway in the San Francisco Bay area.

• IDM dataset: We adopt the IDM simulation model from [42] and [57], where HVs drive on a one-direction road. The road width is set to 3.75 m. To ensure the HVs do not exceed the $\mathrm { E V } \mathbf { \bar { s } }$ maximum acceleration and deceleration capabilities, the maximum and minimum longitudinal acceleration of HVs are set to $3 \mathrm { m } / \mathrm { s } ^ { 2 }$ and $- 4 \mathrm { m } / \mathrm { s } ^ { 2 }$ , respectively. The initial and desired longitudinal velocity ranges of HVs are set to [7 m/s, 22 m/s] and [7 m/s, 28.5 m/s] with a random setting for cruise and racing tasks, respectively. The number of HVs is set to 18, positioned within the longitudinal range from - 50 m to 130 m relative to the longitudinal position of the EV. Additionally, we initialize their states at the starting point of a fixed and safe lane with zero acceleration and steering angle.

• The NGSIM dataset2 consists of 46 HVs. The HVs drive on a six-lane and one-direction road, where the road width is set to 4 m for our experiments. Collected from the I-80 freeway in the San Francisco Bay area, the dataset exhibits multi-modal driving behaviors, including lane changing and instances of urgent acceleration and deceleration. The data was captured at a timestep of 0.08 s, ensuring a high temporal resolution for the experiments.

2) Parameters and Baselines: For each detected HV, we just employ a simple constant velocity prediction model to predict its motion in Algorithm 1 and Algorithm 2. Although more state-of-the-art motion prediction models could be implemented for surrounding HVs, our constant prediction model aims to showcase the real-time adaptability and robustness of the proposed BPHTO approach to various uncertain driving scenarios. Each element in the smoothness weighting matrices $\mathbf { Q } _ { \theta } , \mathbf { Q } _ { \lambda }$ x and $\mathbf { Q } _ { y }$ is set to 200, 100, and 100 respectively; $K _ { \mathrm { m a x } } = 1 5 0 ; { \epsilon } ^ { \mathrm { { \scriptsize { p r i } } } } = 0 . 1$ . All initial values in dual variable vectors $\lambda _ { \theta } , \lambda _ { \mathrm { o b s } , x } , \lambda _ { \mathrm { o b s } , y } , \lambda _ { x } , \lambda _ { y }$ are set to zero. The initial barrier coefficient parameter $\alpha _ { 0 }$ is set to 0.2, which linearly increases to 1 along the planning horizon $N ,$ resulting in $\alpha _ { N - 1 } = 1$ . The desired lateral position range regarding road boundaries is set to $p _ { y } \in [ - 8 \mathrm { m } , 8 \mathrm { m } ]$ . Each element in the $\mathbf { L } _ { x }$ and $\mathbf { L } _ { y }$ matrices is configured to be 6 m and 5.5 m for constructing the BFs, respectively. The maneuver adjustment vector $\delta \mathbf { y } = [ - 6 \mathrm { m } \quad - 3 \mathrm { m }$ 0 m 3 m 6 m].

When interacting with HVs with the IDM dataset, the target longitudinal and lateral jerk range of the EV are set

1https://data.transportation.gov/Automobiles/Next-Generation-Simulation-NGSIM-Vehicle-Trajector/8ect-6jqj

2https://shorturl.at/aLX03

TABLE I PARAMETERS IN THE DRIVING EXPERIMENTS 

<table><tr><td>Description</td><td>Parameter with value</td></tr><tr><td>Front axle distance to center of mass</td><td> $l_{f}=1.06\mathrm{m}$ </td></tr><tr><td>Rear axle distance to center of mass</td><td> $l_{r}=1.85\mathrm{m}$ </td></tr><tr><td>Safety checking parameters</td><td> $a_{i}=5.5\mathrm{m}, b_{i}=4\mathrm{m}$ </td></tr><tr><td>Lane width using IDM datasets</td><td> $w_{l}=3.75\mathrm{m}$ </td></tr><tr><td>Lane width using NGSIM datasets</td><td> $w_{l}=4\mathrm{m}$ </td></tr><tr><td>Lateral perception range</td><td> $r_{p}=8\mathrm{m}$ </td></tr><tr><td>Anticipated number of nearest HVs</td><td> $M=5$ </td></tr><tr><td>Order and dimension of Bézier curves</td><td> $n=10, m=3$ </td></tr><tr><td>Longitudinal position range</td><td> $p_{x}\in[-500\mathrm{m},1000\mathrm{m}]$ </td></tr><tr><td>Longitudinal velocity range</td><td> $v_{lon}\in[0\mathrm{m/s},24\mathrm{m/s}]$ </td></tr><tr><td>Longitudinal acceleration range</td><td> $a_{x}\in[-4\mathrm{m/s^{2}},3\mathrm{m/s^{2}}]$ </td></tr><tr><td>Lateral acceleration range</td><td> $a_{y}\in[-2\mathrm{m/s^{2}},2\mathrm{m/s^{2}}]$ </td></tr><tr><td>Longitudinal jerk range</td><td> $j_{x}\in[-2\mathrm{m/s^{3}},2\mathrm{m/s^{3}}]$ </td></tr><tr><td>Lateral jerk range</td><td> $j_{y}\in[-1.5\mathrm{m/s^{3}},1.5\mathrm{m/s^{3}}]$ </td></tr><tr><td> $l_{2}$ penalty parameter</td><td> $\rho_{\theta}=\rho_{x}=\rho_{y}=\rho_{\mathrm{obs},x}=\rho_{\mathrm{obs},y}=5$ </td></tr><tr><td>Trajectory evaluation vector</td><td> $\mathbf{w}=[200\quad 20\quad 40\quad 20\quad 20]^{T}$ </td></tr></table>

to $[ - 0 . 9 \mathrm { m / s ^ { 3 } } , 0 . 9 \mathrm { m / s ^ { 3 } } ]$ and $[ - 0 . 6 \mathrm { m } / \mathrm { s } ^ { 3 } , 0 . 6 \mathrm { m } / \mathrm { s } ^ { 3 } ]$ for driving stability consideration. For NGSIM datasets with highly maneuverable and uncertain HVs and static scenarios with higher relative speeds, the longitudinal jerk ranges are configured with larger values, specifically $[ - 1 . 5 \mathrm { m } / \mathrm { { s } } ^ { 3 } , 1 . 5 \mathrm { m } / \mathrm { s } ^ { 3 } ]$ and $[ - 1 . 0 \mathrm { m / s } ^ { 3 } , 1 . 0 \mathrm { m / s } ^ { 3 } ]$ , respectively. However, for stable merging, the longitudinal and lateral jerk sets are set to $[ - 0 . 9 \mathrm { m } / \mathrm { s } ^ { 3 } , 0 . 9 \mathrm { m } / \mathrm { s } ^ { 3 } ]$ and $[ - 0 . 6 \mathrm { m } / \mathrm { s } ^ { 3 } , \dot { 0 } . 6 \mathrm { m } / \mathrm { s } ^ { 3 } ]$ , respectively. The planning horizon in IDM and NGSIM datasets is set to $N = 5 0$ and $N = 6 0 .$ , respectively. The initial longitudinal velocity is set to 15 m/s with a zero heading angle for all scenarios. The communication and control frequency for IDM and NGSIM datasets are set to 0.1 Hz and 0.08 Hz, respectively. Other parameters of the experiments are presented in Table I.

To validate the effectiveness of the proposed BPHTO scheme, we compare it against two baselines. The first baseline is an ablated version of BPHTO, denoted as BTO, which includes only one trajectory without free-end homotopic trajectories. The second baseline is a multi-modal MPC algorithm: Batch-MPC [42] tailored for highway scenarios based on Bergman alternating minimization. Open-source $\mathrm { c o d e } ^ { 3 }$ is leveraged to configure parallel trajectories and optimize parameters for optimal performance.

# B. Comparative Results

In this section, we compare the performance of our algorithm with other baselines under static and dynamic dense traffic in cruise tasks. The target longitudinal velocity is set to $v _ { \mathrm { d } } = 1 5 \mathrm { m / s }$ . The assessment criteria encompass several key indicators, including the average cruise speed, mean absolute longitudinal jerk value, and the rate of frequent lane changes between two consecutive decision-making instants.

1) Navigation in Static Environments: This EV is required to navigate through a dense obstacle scenario with relatively high speeds to static obstacles. Each section within the longitudinal range from −50 m to 130 m relative to the longitudinal position of the EV is configured with ten vehicle-shaped obstacles. The initial position of the EV is set to [−20 m 0 m]. The target lateral for each trajectory of Batch-MPC is set to $\left[ - 7 . 5 \mathrm { m } \quad - 3 . 7 5 \mathrm { m } \quad 0 \mathrm { m } \quad 3 . 7 5 \mathrm { m } \quad 7 . 5 \mathrm { m } \right]$ , with each

3https://github.com/vivek-uka/Batch-Opt-Highway-Driving optimized trajectory corresponding to the centerline of a driving lane. The simulation time is set to 30 s.

TABLE IIPERFORMANCE COMPARISON AMONG DIFFERENT ALGORITHMS INDENSE AND CLUTTERED STATIC SCENARIO

<table><tr><td rowspan="2">Algorithm</td><td rowspan="2">Accuracy $V_{mean}$  (m/s)</td><td colspan="3">Stability</td></tr><tr><td> $J_{mean}$  (m/s3)</td><td> $J_{max}$  (m/s3)</td><td> $P_c$  (%)</td></tr><tr><td>Batch-MPC</td><td>14.78</td><td>1.62</td><td>27.06</td><td>18</td></tr><tr><td>BTO</td><td>15.25</td><td>0.46</td><td>1.40</td><td>-</td></tr><tr><td>BPHTO</td><td>15.02</td><td>0.33</td><td>1.40</td><td>0.57</td></tr></table>

Table II presents the static performance comparison results of three algorithms in static environments. The results reveal that BPHTO achieves more stable driving behaviors with a lower jerk value and better driving consistency, quantified by the rate of frequent lane changes $\mathcal { P } _ { d } = 0 . 5 7 $ %. In contrast, Batch-MPC exhibits a frequent lane changes rate $\mathcal { P } _ { d } = 1 8 \%$ , and the largest jerk value is up to around $2 7 \mathrm { m } / \mathrm { s } ^ { 3 }$ , showing aggressive driving behaviors. Besides, BPHTO achieves the best cruise accuracy among the three algorithms with respect to the desired cruise speed of 15 m/s. Compared with BTO, BPHTO demonstrates improved cruise accuracy, suggesting that employing multiple free-end homotopic trajectories for decision-making enhances task accuracy.

2) Navigation in Dynamic Dense Traffic: We further compare the performance of three different algorithms using synthetic IDM and real-world NGSIM datasets. The simulation employs a time step of 350, resulting in simulation durations of 35 s and 28 s with the IDM and NGSIM datasets, respectively. The target lateral for Batch-MPC is set to the centerline position of each driving lane. The initial position of the EV is set to [−40 m 0 m] and [70 m 6 m] with IDM and NGSIM datasets, respectively.

Table III shows that the average cruise speed of the EV based on BPHTO is closest to the desired cruise speed 15 m/s among three algorithms, indicating superior cruise accuracy. Notably, Batch-MPC exhibits a larger maximum longitudinal jerk value $( \mathcal { I } _ { m e a n } = 1 2 \mathrm { m } / \mathrm { s } ^ { 3 } )$ and a higher percentage of the rate of frequent lane changes $( \mathcal { P } _ { d } = 2 2 . 5 7 \% )$ , indicating that the EV frequently changes its target goal lane, resulting in inferior cruise stability and driving consistency. This finding is supported by the evolution of the longitudinal jerk and acceleration profile depicted in Fig. 2.

Compared with BTO algorithm, BPHTO achieves better cruise accuracy in both static and dynamic cruise cases using IDM and NGSIM datasets. These observations demonstrate that BPHTO with multiple free-end homotopic trajectories efficiently explores different driving lanes and significantly improves cruise performance.

Overall, these results showcase the effectiveness of BPHTO in ensuring both high task performance and safety amid challenging dense traffic flow, utilizing IDM and real-world traffic datasets.

# C. Safety Evaluation

1) Reacting to Road Construction: To further highlight the capabilities of our proposed BPHTO to adapt to varying driving environments, we designed a road construction scenario within a cruise task under dense traffic. HVs are controlled in the same manner as described in Section VI-B2 using the IDM dataset. Navigating through such cluttered environments presents a substantial challenge for autonomous vehicles [2], [58]. Due to the inability of other baselines to handle this situation, we do not present their results here. The initial position vector of the EV is set to [0 m $5 \mathrm { m } ] ^ { T }$ , and its front lane is under construction starting at a longitudinal position of 150 m, with lateral positions ranging from 1.875 m to 9.375 m.

![](images/53d9a6019aa0ae9ab759501ae87b497c2fc890b0aac6d7d413cc5c8cba164dae.jpg)

<details>
<summary>line</summary>

| Global X (m) | BTO    | BPHTO  | Batch-MPC |
| ------------ | ------ | ------ | --------- |
| 0            | 0.0    | 0.0    | 0.0       |
| 100          | -5.0   | 5.0    | 3.0       |
| 200          | -2.0   | 6.0    | 5.0       |
| 300          | 2.0    | 1.0    | 1.0       |
| 400          | -2.0   | -1.0   | 0.0       |
| 500          | -1.0   | -2.0   | 1.0       |
</details>

![](images/1c8d52423e6b4efdf7bd4359b786044ac698a993a7cd6fdd19ee63377cacb103.jpg)

<details>
<summary>line</summary>

| Time (s) | Heading Angle (rad) - Solid Green | Heading Angle (rad) - Dashed Red | Heading Angle (rad) - Dash-Dot Purple |
| -------- | ---------------------------------- | --------------------------------- | ------------------------------------- |
| 0        | 0.00                               | 0.00                              | 0.00                                  |
| 5        | 0.05                               | 0.10                              | 0.05                                  |
| 10       | 0.00                               | 0.05                              | 0.05                                  |
| 15       | 0.05                               | -0.05                             | -0.05                                 |
| 20       | 0.10                               | -0.10                             | 0.00                                  |
| 25       | -0.05                              | -0.05                             | -0.05                                 |
| 30       | 0.00                               | 0.00                              | 0.05                                  |
| 35       | 0.05                               | 0.05                              | -0.05                                 |
</details>

![](images/42120440e343c53b10e058f8ea8a76314d60cbdc0b856428442ae3ef27eab649.jpg)

<details>
<summary>line</summary>

| Time (s) | Jerk (m/s²) |
| -------- | ----------- |
| 0        | 0           |
| 5        | 0           |
| 10       | 0           |
| 15       | 0           |
| 20       | 0           |
| 25       | 0           |
| 30       | 0           |
| 35       | 0           |
</details>

Fig. 2. Comparison of position, heading angle, and longitudinal jerk profiles when executing a cruise task using IDM dataset for surrounding HVs’ motion. The evolution of the heading angle profiles reveals how the EV adjusts its orientation to navigate through dense and dynamic traffic.

![](images/d7186211b7bbb2ae0926bb83567cd406577c5195ccb26a0682c60dda9511fcf5.jpg)

<details>
<summary>line</summary>

| Global X (m) | Global Y (m) | Longitudinal Velocity (m/s) |
| ------------ | ------------ | --------------------------- |
| 0            | 3.75         | 16.0                        |
| 50           | 3.75         | 16.0                        |
| 100          | 3.75         | 16.0                        |
| 150          | 0.00         | 15.5                        |
| 200          | -3.75        | 15.0                        |
| 250          | -3.75        | 15.0                        |
| 300          | -3.75        | 15.0                        |
</details>

Fig. 3. Evolution of the trajectory in the road construction scenario when executing a cruise task using IDM dataset for surrounding HVs’ motion. The motion trajectory of the EV over a simulation duration of 20 s is colored according to its longitudinal speed profile (yellow-red color).

The motion trajectory of the EV in Fig. 3 demonstrates its ability to maneuver and avoid the road construction area ahead. Notably, a change in trajectory orientation and an increase in longitudinal velocity around longitudinal position 75 m indicate the EV proactively adjusts its orientation and speed to move swiftly into the construction-free lane below. Additionally, the cruise speed consistently maintains proximity to the targeted speed of 15 m/s. This outcome further underscores the EV’s capacity to proactively adjust its driving lane while keeping a stable cruise speed.

2) Safety Recovery: This subsection assesses the performance of BPHTO in terms of driving stability and safety recovery during a challenging lane-merging conflict scenario under a cruise task. The motion of HVs is derived from real-world data in the NGSIM dataset with larger control limits than the EV. The simulation time is set to 19.2 s, spanning 240 steps and divided into two distinct phases. In Phase 1, the autonomous red EV endeavors to change lanes and merge with the upper lane 2, where the nearest detected HV is the orange HV1. Simultaneously, an imperceptible blue HV2 in lane 1 executes a lane change to lane 2, as depicted in Fig. 4. Phase 2 focuses on the EV’s response to the cut-in by HV2, requiring a stable speed adjustment to recover and maintain a safe following distance exceeding 20 m.

TABLE IIIPERFORMANCE COMPARISON AMONG DIFFERENT ALGORITHMS IN IDM AND NGSIM DATASETS

<table><tr><td rowspan="3">Algorithm</td><td colspan="4">IDM dataset</td><td colspan="4">NGSIM dataset</td></tr><tr><td rowspan="2">Accuracy $V_{mean}$  (m/s)</td><td colspan="3">Stability</td><td rowspan="2">Accuracy $V_{mean}$  (m/s)</td><td colspan="3">Stability</td></tr><tr><td> $\mathcal{J}_{mean}$  (m/s3)</td><td> $\mathcal{J}_{max}$  (m/s3)</td><td> $\mathcal{P}_{c}$  (%)</td><td> $\mathcal{J}_{mean}$  (m/s3)</td><td> $\mathcal{J}_{max}$  (m/s3)</td><td> $\mathcal{P}_{c}$  (%)</td></tr><tr><td>Batch-MPC</td><td>14.94</td><td>0.38</td><td>12.68</td><td>22.57</td><td>15.060</td><td>1.58</td><td>35.52</td><td>35.43</td></tr><tr><td>BTO</td><td>15.31</td><td>0.27</td><td>0.94</td><td>-</td><td>15.408</td><td>0.40</td><td>1.496</td><td>-</td></tr><tr><td>BPHTO</td><td>15.02</td><td>0.25</td><td>0.95</td><td>0.57</td><td>14.997</td><td>0.26</td><td>1.46</td><td>0.86</td></tr></table>

![](images/7218b533a6f88566ae48a475e2d6d76a7a8f594eb95ef25f08cfbd7acbac8970.jpg)

<details>
<summary>flowchart</summary>

```mermaid
graph TD
    A["Car 1"] --> B["Car 2"]
    C["Car 2"] --> D["Car 3"]
    E["Car 3"] --> F["Car 4"]
    style A fill:#f9f,stroke:#333
    style C fill:#f9f,stroke:#333
    style E fill:#f9f,stroke:#333
    style F fill:#f9f,stroke:#333
```
</details>

Fig. 4. A lane-merging conflict scenario. The red EV in lane 3 is in the process of executing a lane change to lane 2, while an imperceptible blue HV2 in lane 1 is initiating a lane change to lane 2 from a different direction, potentially leading to a hazardous situation.

![](images/f17a5ce125547b12f61589da4400ef55c9c68e9f70c1a94fdcfbdfcd3bcf25a0.jpg)

<details>
<summary>line</summary>

| Global X (m) | Global Y (m) | Longitudinal Velocity (m/s) |
| ------------ | ------------ | --------------------------- |
| 25           | 2            | 5                           |
| 50           | 3            | 10                          |
| 75           | 5            | 15                          |
| 100          | 7            | 18                          |
| 125          | 8            | 20                          |
| 150          | 8            | 20                          |
| 175          | 8            | 20                          |
| 200          | 8            | 20                          |
</details>

Fig. 5. Evolution of trajectory when executing a lane merge task under cruise scenario using NGSIM dataset for surrounding HVs’ motion. It displays the trajectory of the EV, colored according to its longitudinal speed profile (yellow-red color).

The trajectory and longitudinal velocity evolution are depicted in Fig. 5, illustrating velocity changes at different positions during interactions with abrupt cut-in HVs. To obtain an intuitive understanding of this adjustment, Fig. 6 shows the corresponding velocity and acceleration profiles of two HVs and the EV. Notably, at the commencement of Phase 2 (around 1.2 s), the EV decelerates to reduce its longitudinal velocity, demonstrating a proactive response to the abrupt cut-in by HV2, which has a larger acceleration range. The EV adaptively adjusts its longitudinal velocity in sync with the front HV2’s evolution, ensuring a safe following distance. Additionally, in Fig. 7, it is observed that the longitudinal and lateral jerk values are consistently maintained within a suitably configured range for the majority of the time. This demonstrates that the EV can stably react to the sudden cut-in by HV when performing lane-changing behaviors.

![](images/80fcce59ce45cf7076a0706c97acb2c03e709b9d152d3456a119fc2f601c9f0b.jpg)

<details>
<summary>line</summary>

| Time (s) | HV1  | HV2  | EV   |
| -------- | ---- | ---- | ---- |
| 0.0      | 10.0 | 15.0 | 15.0 |
| 2.5      | 12.0 | 13.0 | 12.0 |
| 5.0      | 11.0 | 12.0 | 11.0 |
| 7.5      | 10.0 | 13.0 | 10.0 |
| 10.0     | 9.0  | 11.0 | 9.0  |
| 12.5     | 7.0  | 8.0  | 7.0  |
| 15.0     | 6.0  | 6.0  | 5.0  |
| 17.5     | 7.0  | 7.0  | 6.0  |
| 20.0     | 8.0  | 8.0  | 7.0  |
</details>

![](images/2f9a226c355e33a72e62833a7f5bfcd67e31081581143a70db1a890b6fe8bf3f.jpg)

<details>
<summary>line</summary>

| Time (s) | Longitudinal Acceleration (m/s²) |
| -------- | -------------------------------- |
| 0.0      | 0.0                              |
| 2.5      | -5.0                             |
| 5.0      | 0.0                              |
| 7.5      | 5.0                              |
| 10.0     | 0.0                              |
| 12.5     | -5.0                             |
| 15.0     | 0.0                              |
| 17.5     | 5.0                              |
| 20.0     | 0.0                              |
</details>

Fig. 6. Evolution of velocity and acceleration profiles of the EV and its nearest front HVs when executing a lane merge task using NGSIM dataset for surrounding HVs’ motion. The similarities in the velocity profile indicate how the EV attempts to adjust its velocity to keep a desired following distance with its front HV.

![](images/f22b2900c96d0835d5244f982fbe9cc7aecab05ef640c20e176f22aab0074ed5.jpg)

<details>
<summary>line</summary>

| Time (s) | Longitudinal Jerk (m/s³) | Lateral Jerk (m/s³) |
| -------- | ------------------------ | ------------------- |
| 0.0      | -0.6                     | -0.9                |
| 2.5      | 0.9                      | -0.7                |
| 5.0      | 0.8                      | -0.4                |
| 7.5      | 0.8                      | -0.2                |
| 10.0     | 0.8                      | 0.3                 |
| 12.5     | 0.8                      | 0.5                 |
| 15.0     | 0.8                      | 0.2                 |
| 17.5     | 0.8                      | 0.1                 |
| 20.0     | 0.8                      | 0.1                 |
</details>

Fig. 7. Evolution of the longitudinal and lateral jerk profiles. The longitudinal and lateral jerk values lie within the desired boundary $[ - 0 . 9 \mathrm { m } / \mathrm { s } ^ { 3 } , 0 . 9 \mathrm { m } / \mathrm { s } ^ { 3 } ]$ and $[ - 0 . 6 \mathrm { m } / \mathrm { s } ^ { 3 } , 0 . 6 \mathrm { m } / \mathrm { s } ^ { 3 } ]$ for most of the time.

Figure 8 visualizes the computed longitudinal distance to the nearest leading HV in two phases. Notably, the distance between the EV and HV2 violates the safety barrier value at the beginning and at around 12 s. The initial violation stems from the sudden cut-in maneuver of the imperceptible HV2 at the beginning of Phase 2, while the subsequent breach is due to the front HV2’s abrupt deceleration, surpassing the EV’s maximum allowable deceleration limit, as illustrated in Fig. 6. After the first violation, the EV endeavors to decrease its speed to increase its following distance. However, the HV2 exhibits significant deceleration values from 1.4 s to 2.3 s, surpassing the maximum allowable deceleration of the EV, as depicted in Fig. 6. Consequently, the following distance experiences a slight decrease from 1.6 s to 2.5 s. After that, the following distance asymptotically converges to the desired value 20 m. The second violation is attributed to the severe deceleration fluctuation of the front HV2, leading to a decrease in the following distance. Following this violation, the EV stably adjusts its speed to achieve the desired following distance. These findings demonstrated our algorithm’s robustness and safety recovery capabilities in response to unexpected safety barrier violations.

![](images/d2b2add6d5380703ab9857a459003d9e80744f51d9bc6a480ab1d292ffe202b7.jpg)

<details>
<summary>line</summary>

| Time (s) | Distance to HV1 (m) | Distance to HV2 (m) |
| -------- | ------------------- | ------------------- |
| 0.0      | 37.0                | -                   |
| 1.0      | 34.0                | -                   |
| 2.0      | 14.0                | -                   |
| 3.0      | -                   | -                   |
| 4.0      | -                   | -                   |
| 5.0      | -                   | -                   |
| 6.0      | -                   | -                   |
| 7.0      | -                   | -                   |
| 8.0      | -                   | -                   |
| 9.0      | -                   | -                   |
| 10.0     | -                   | -                   |
| 11.0     | -                   | -                   |
| 12.0     | -                   | -                   |
| 13.0     | -                   | -                   |
| 14.0     | -                   | -                   |
| 15.0     | -                   | -                   |
| 16.0     | -                   | -                   |
| 17.0     | -                   | -                   |
| 18.0     | -                   | -                   |
| 19.0     | -                   | -                   |
| 20.0     | -                   | -                   |
</details>

Fig. 8. Evolution of the headway when executing a lane-merging task under cruise scenario using the NGSIM dataset for surrounding $\mathrm { H V } \bar { \bf s } ^ { \prime }$ motion. The dashed line denotes the safety barrier value during driving.

In this lane-merging conflict scenario, where sudden maneuvers by HVs caused safety barrier violations, our algorithm demonstrates real-time adaptability by promptly adjusting the EV’s speed to proactively address these safety issues. Despite transient decreases in the safety barrier value, the algorithm dynamically stabilized the situation, emphasizing its commitment to continuous safety improvement. This underscores the algorithm’s robustness and safety recovery capabilities in addressing unexpected scenarios, reinforcing its reliability in enhancing safety within complex and dynamic driving environments.

# VII. DISCUSSIONS

# A. Real-Time Performance

To evaluate the computational efficiency of our BPHTO framework, we manipulate the number of free-end homotopic trajectories $N _ { c }$ and the nearest M HVs considered in cruise tasks where the setting is the same as Section VI-B2. This allows us to analyze the computational time required across various simulation setups.

As depicted in Fig. 9(a), a linear increase is observed in the average optimization time concerning the number of homotopic candidate trajectories. Given our current practice of employing a single thread for optimizing multiple trajectories, one can facilitate computational efficiency through the application of multi-threading techniques in engineering applications. Additionally, we can notice that the average computation time of BPHTO is less than 100 ms with the prediction length $N = 5 0$ , as illustrated in Fig. 9(b). These results indicate that our BPHTO algorithm attains real-time performance while handling different levels of density of obstacles. This efficiency is a key factor in ensuring real-time performance of our framework in dynamic and evolving traffic environments.

![](images/c0a0ce33e16498814dc28443be75383a4ea6900431aa558387dd58695b8c7012.jpg)

<details>
<summary>boxplot</summary>

| Number of Homotopic Trajectories | Computation Time (ms) |
| --------------------------------- | --------------------- |
| 2                                 | ~20–30                |
| 3                                 | ~35–45                |
| 4                                 | ~50–60                |
| 5                                 | ~55–65                |
| 6                                 | ~65–75                |
</details>

(a)

![](images/c8fe9aac7503cf5355da71e7c68a4aeb8cf9c074c15802d42dd4d909c4c90684.jpg)

<details>
<summary>boxplot</summary>

| Number of Obstacles | Computation Time (ms) |
| ------------------- | --------------------- |
| 3                   | 50                    |
| 4                   | 52                    |
| 5                   | 58                    |
| 6                   | 65                    |
| 7                   | 75                    |
</details>

(b)

Fig. 9. Statistical results of the computation time per cycle with planning horizon $N = 5 0 .$ . (a) Different number of homotopic trajectories $N _ { c }$ . (b) Different numbers of nearest considered $\mathrm { H V s }$ with five homotopic trajectories.   
![](images/186cd9efbf8475abd65a52c7d915078d3726ec15bd40c9db78387ddd9f5ae408.jpg)

<details>
<summary>line</summary>

| Time (s) | Batch-MPC | BPHTO |
| -------- | --------- | ----- |
| 0        | 6         | 5     |
| 1        | 2         | 6     |
| 2        | 6         | 5     |
| 3        | 6         | 5     |
| 4        | 4         | 6     |
| 5        | 4         | 5     |
| 6        | 4         | 5     |
| 7        | 4         | 5     |
| 8        | 5         | 4     |
| 9        | 3         | 3     |
| 10       | 2         | 2     |
| 11       | 6         | 3     |
| 12       | 6         | 4     |
| 13       | 6         | 4     |
| 14       | 6         | 4     |
| 15       | 6         | 4     |
| 16       | 6         | 4     |
| 17       | 6         | 4     |
| 18       | 6         | 4     |
| 19       | 6         | 4     |
| 20       | 6         | 4     |
| 21       | 6         | 4     |
| 22       | 6         | 4     |
| 23       | 6         | 4     |
| 24       | 6         | 4     |
| 25       | 6         | 4     |
| 26       | 6         | 4     |
| 27       | 6         | 4     |
| 28       | 6         | 4     |
</details>

Fig. 10. Evolution of the target lane when executing an adaptive cruise under dense traffic using NGSIM dataset for surrounding HVs’ motion.

# B. Driving Consistency

To gain a more intuitive interpretation of driving consistency, the decision-making process illustrated in Fig. 10 delineates the evolution of the target lane during the cruise in Section VI-B2. Notably, Batch-MPC exhibits a tendency to frequently switch between different driving lanes in various directions, with some instances involving shifts across more than one lane. A prominent example is observed at 1.7 s, where Batch-MPC switches the target driving lane from lane 5 to lane 2. In contrast, BPHTO showcases a more consistent driving behavior, with no abrupt lane changes detected between two consecutive decision-making instants for the majority of the duration. The singular exception occurs at 1.9 s, where BPHTO undergoes a lane change between two adjacent lanes: lane 5 and lane 6. This observation underscores the enhanced driving consistency achieved by BPHTO.

# VIII. CONCLUSION

This paper presents an integrated decision-making and planning scheme with the BPHTO algorithm for real-time safety-critical autonomous driving. The framework leverages BF and reachability analysis to enhance safety interactions and driving stability. BPHTO is then designed to optimize multiple behavior-oriented nominal trajectories concurrently in real time through the over-relaxed ADMM algorithm. The effectiveness of BPHTO is verified through various cruise control driving tasks, utilizing both real-world and synthetic datasets compared to baseline approaches, with the attendant outcome of improved task accuracy, driving stability, and consistency. Notably, BPHTO demonstrates robust safety recovery capabilities after abrupt interventions by HVs and the ability to navigate cluttered road construction areas. The real-time performance and driving consistency of the proposed BPHTO are thoroughly discussed in the context of cruise control tasks. As part of our future work, we plan to extend the algorithm to accommodate perception uncertainties in urban environments to achieve safe autonomous driving.

# APPENDIX

# DERIVATION OF LONGITUDINAL DISTANCE CHANGES

In Case 1, the maximum longitudinal acceleration $a _ { x . }$ ,max is not reached while the desired longitudinal velocity $v _ { d }$ is reached. Then, the time intervals of the acceleration, deceleration, and constant segments can be computed as:

$$
t _ {a} = \frac {a _ {1} - a _ {x , 0}}{\dot {j} _ {x , \max}}, \tag {53a}
$$

$$
t _ {d} = \frac {a _ {1}}{- j _ {x , \min}} = \frac {a _ {1}}{j _ {x , \max}}, \tag {53b}
$$

$$
t _ {c} = T - t _ {a} - t _ {d}, \tag {53c}
$$

where the temporary maximum acceleration $a _ { 1 }$ is to be computed. Additionally, we can get the velocity change as the integral of acceleration with respect to time as follows:

$$
\Delta V = v _ {\mathrm{d}} - v _ {x, 0} = \frac {(2 t _ {a} + t _ {d}) \times a _ {1} - (a _ {1} - a _ {x , 0}) \times t _ {a}}{2}. \tag {54}
$$

Substituting the time segments (53) into (55), we can get the value of $a _ { 1 }$ as follows:

$$
a _ {1} = \sqrt {\frac {2 \Delta V j _ {x , \max} + a _ {x , 0} ^ {2}}{2}}. \tag {55}
$$

As a result, the corresponding longitudinal distance changes in Case 1 can be derived as:

$$
\begin{array}{l} \delta p _ {x} = v _ {x, 0} t _ {a} + \frac {a _ {x , 0} + a _ {1}}{4} t _ {a} ^ {2} + \left(v _ {x, 0} + \frac {a _ {x , 0} + a _ {1}}{2} t _ {a}\right) t _ {d} \\ + \frac {a _ {1}}{4} t _ {d} ^ {2} + v _ {\mathrm{d}} t _ {c}. \tag {56} \\ \end{array}
$$

In Case 2, the maximum longitudinal acceleration $a _ { x , \mathrm { m a x } } \ \mathrm { i s }$ reached while the maximum velocity needs to be computed. Then, the time intervals of the acceleration, constant, and deceleration segments can be analytically obtained as follows:

$$
t _ {a} = \frac {a _ {x , \max} - a _ {x , 0}}{j _ {x , \max}}, \tag {57a}
$$

$$
t _ {c} = \frac {a _ {x , \max}}{- j _ {x , \min}} = \frac {a _ {x , \max}}{j _ {x , \max}}, \tag {57b}
$$

$$
t _ {d} = T - t _ {a} - t _ {d}. \tag {57c}
$$

Similarly, it gives

$$
\begin{array}{l} \Delta V = \frac {\left(a _ {x , 0} + a _ {x , \max}\right) t _ {a} + 2 a _ {x , \max} t _ {c} + a _ {x , \max} t _ {d}}{2} \\ = \frac {a _ {x , 0} t _ {a} + a _ {x , \max} (t _ {a} + 2 t _ {c} + t _ {d})}{2}. \tag {58} \\ \end{array}
$$

Then, the corresponding longitudinal distance changes in Case 2 can be derived as:

$$
\begin{array}{l} \delta p _ {x} = v _ {x, 0} t _ {a} + \frac {a _ {x , 0} + a _ {x , \mathrm{max}}}{4} t _ {a} ^ {2} \\ + \left(v _ {x, 0} + \frac {a _ {x , 0} + a _ {x , \max}}{2} t _ {a}\right) t _ {c} + \frac {a _ {x , \max}}{2} t _ {c} ^ {2} \\ \end{array}
$$

$$
\begin{array}{l} + \left(v _ {x, 0} + \frac {a _ {x , 0} + a _ {x , \max}}{2} t _ {a} + a _ {x, \max} t _ {c}\right) t _ {d} \\ + \frac {a _ {x , \max}}{4} t _ {d} ^ {2}. \tag {59} \\ \end{array}
$$

# REFERENCES

[1] L. Claussmann, M. Revilloud, D. Gruyer, and S. Glaser, “A review of motion planning for highway autonomous driving,” IEEE Trans. Intell. Transp. Syst., vol. 21, no. 5, pp. 1826–1848, May 2020.   
[2] L. Chen et al., “Milestones in autonomous driving and intelligent vehicles: Survey of surveys,” IEEE Trans. Intell. Vehicles, vol. 8, no. 2, pp. 1046–1056, Feb. 2023.   
[3] L. Gharavi, A. Dabiri, J. Verkuijlen, B. De Schutter, and S. Baldi, “Proactive emergency collision avoidance for automated driving in highway scenarios,” 2023, arXiv:2310.17381.   
[4] S. Kousik, B. Zhang, P. Zhao, and R. Vasudevan, “Safe, optimal, realtime trajectory planning with a parallel constrained Bernstein algorithm,” IEEE Trans. Robot., vol. 37, no. 3, pp. 815–830, Jun. 2021.   
[5] B. Paden, M. Cáp, S. Z. Yong, D. Yershov, and E. Frazzoli, “A survey of ˇ motion planning and control techniques for self-driving urban vehicles,” IEEE Trans. Intell. Vehicles, vol. 1, no. 1, pp. 33–55, Mar. 2016.   
[6] L. Zheng, R. Yang, Z. Peng, M. Yu Wang, and J. Ma, “Spatiotemporal receding horizon control with proactive interaction towards autonomous driving in dense traffic,” 2023, arXiv:2308.05929.   
[7] Y. Chen, G. Li, S. Li, W. Wang, S. E. Li, and B. Cheng, “Exploring behavioral patterns of lane change maneuvers for human-like autonomous driving,” IEEE Trans. Intell. Transp. Syst., vol. 23, no. 9, pp. 14322–14335, Sep. 2022.   
[8] P. Hang, Y. Zhang, and C. Lv, “Brain-inspired modeling and decision-making for human-like autonomous driving in mixed traffic environment,” IEEE Trans. Intell. Transp. Syst., vol. 24, no. 10, pp. 10420–10432, May 2023.   
[9] J. Zhou, B. Olofsson, and E. Frisk, “Interaction-aware motion planning for autonomous vehicles with multi-modal obstacle uncertainty predictions,” IEEE Trans. Intell. Vehicles, vol. 9, no. 1, pp. 1305–1319, Jan. 2024.   
[10] J. Ma, Z. Cheng, X. Zhang, M. Tomizuka, and T. H. Lee, “Alternating direction method of multipliers for constrained iterative LQR in autonomous driving,” IEEE Trans. Intell. Transp. Syst., vol. 23, no. 12, pp. 23031–23042, Dec. 2022.   
[11] Z. Huang, S. Shen, and J. Ma, “Decentralized iLQR for cooperative trajectory planning of connected autonomous vehicles via dual consensus ADMM,” IEEE Trans. Intell. Transp. Syst., vol. 24, no. 11, pp. 12754–12766, Nov. 2023.   
[12] L. Gharavi, B. De Schutter, and S. Baldi, “Efficient MPC for emergency evasive maneuvers, Part I: Hybridization of the nonlinear problem,” 2023, arXiv:2310.00715.   
[13] E. Ghadimi, A. Teixeira, I. Shames, and M. Johansson, “Optimal parameter selection for the alternating direction method of multipliers (ADMM): Quadratic problems,” IEEE Trans. Autom. Control, vol. 60, no. 3, pp. 644–658, Mar. 2015.   
[14] W. Schwarting, J. Alonso-Mora, and D. Rus, “Planning and decisionmaking for autonomous vehicles,” Annu. Rev. Control Robot. Auton. Syst., vol. 1, no. 1, pp. 187–210, 2018.   
[15] A. Sadat, M. Ren, A. Pokrovsky, Y. Lin, E. Yumer, and R. Urtasun, “Jointly learnable behavior and trajectory planning for self-driving vehicles,” in Proc. IEEE/RSJ Int. Conf. Intell. Robots Syst. (IROS), Nov. 2019, pp. 3949–3956.   
[16] X. Qian, F. Altché, P. Bender, C. Stiller, and A. de La Fortelle, “Optimal trajectory planning for autonomous driving integrating logical constraints: An MIQP perspective,” in Proc. IEEE 19th Int. Conf. Intell. Transp. Syst. (ITSC), Mar. 2016, pp. 205–210.   
[17] F. Fabiani and S. Grammatico, “Multi-vehicle automated driving as a generalized mixed-integer potential game,” IEEE Trans. Intell. Transp. Syst., vol. 21, no. 3, pp. 1064–1073, Mar. 2020.   
[18] G. Nemhauser and L. Wolsey, Integer and Combinatorial Optimization. New York, NY, USA: Wiley, 1988.   
[19] J. Palatti, A. Aksjonov, G. Alcan, and V. Kyrki, “Planning for safe abortable overtaking maneuvers in autonomous driving,” in Proc. IEEE Int. Intell. Transp. Syst. Conf. (ITSC), Sep. 2021, pp. 508–514.   
[20] Y. Shu, J. Zhou, and F. Zhang, “Safety-critical decision-making and control for autonomous vehicles with highest priority,” in Proc. IEEE Intell. Vehicles Symp. (IV), Jun. 2023, pp. 1–8.

[21] S. He, J. Zeng, B. Zhang, and K. Sreenath, “Rule-based safetycritical control design using control barrier functions with application to autonomous lane change,” in Proc. Amer. Control Conf. (ACC), 2021, pp. 178–185.   
[22] T. Zhang, W. Song, M. Fu, Y. Yang, X. Tian, and M. Wang, “A unified framework integrating decision making and trajectory planning based on spatio-temporal voxels for highway autonomous driving,” IEEE Trans. Intell. Transp. Syst., vol. 23, no. 8, pp. 10365–10379, Aug. 2022.   
[23] C. Liu, S. Lee, S. Varnhagen, and H. E. Tseng, “Path planning for autonomous vehicles using model predictive control,” in Proc. IEEE Intell. Veh. Symp. (IV), 2017, pp. 174–179.   
[24] Q. Wang, B. Ayalew, and T. Weiskircher, “Optimal assigner decisions in a hybrid predictive control of an autonomous vehicle in public traffic,” in Proc. Amer. Control Conf. (ACC), Jul. 2016, pp. 3468–3473.   
[25] Q. Wang, B. Ayalew, and T. Weiskircher, “Predictive maneuver planning for an autonomous vehicle in public highway traffic,” IEEE Trans. Intell. Transp. Syst., vol. 20, no. 4, pp. 1303–1315, Apr. 2019.   
[26] M. Ammour, R. Orjuela, and M. Basset, “A MPC combined decision making and trajectory planning for autonomous vehicle collision avoidance,” IEEE Trans. Intell. Transp. Syst., vol. 23, no. 12, pp. 24805–24817, Dec. 2022.   
[27] Ö. ¸S. Ta¸s, P. H. Brusius, and C. Stiller, “Decision-theoretic MPC: Motion planning with weighted maneuver preferences under uncertainty,” 2023, arXiv:2310.17963.   
[28] L. Zheng, R. Yang, Z. Peng, H. Liu, M. Y. Wang, and J. Ma, “Real-time parallel trajectory optimization with spatiotemporal safety constraints for autonomous driving in congested traffic,” in Proc. IEEE 26th Int. Conf. Intell. Transp. Syst. (ITSC), Sep. 2023, pp. 1186–1193.   
[29] R. Wang, M. Schuurmans, and P. Patrinos, “Interaction-aware model predictive control for autonomous driving,” in Proc. Eur. Control Conf. (ECC), Jun. 2023, pp. 1–6.   
[30] K. Leung, E. Schmerling, M. Chen, J. Talbot, J. C. Gerdes, and M. Pavone, “On infusing reachability-based safety assurance within planning frameworks for human–robot vehicle interactions,” Int. J. Robot. Res., vol. 39, nos. 10–11, pp. 1326–1345, 2020.   
[31] A. D. Ames, S. Coogan, M. Egerstedt, G. Notomista, K. Sreenath, and P. Tabuada, “Control barrier functions: Theory and applications,” in Proc. IEEE 18th Eur. Control Conf. (ECC), May 2019, pp. 3420–3431.   
[32] T. Brudigam, M. Olbrich, D. Wollherr, and M. Leibold, “Stochastic model predictive control with a safety guarantee for automated driving,” IEEE Trans. Intell. Vehicles, vol. 8, no. 1, pp. 22–36, Jan. 2023.   
[33] C. Pek and M. Althoff, “Fail-safe motion planning for online verification of autonomous vehicles using convex optimization,” IEEE Trans. Robot., vol. 37, no. 3, pp. 798–814, Jun. 2021.   
[34] J. Zeng, B. Zhang, and K. Sreenath, “Safety-critical model predictive control with discrete-time control barrier function,” in Proc. Amer. Control Conf., 2021, pp. 3882–3889.   
[35] J. Ma, Z. Cheng, X. Zhang, Z. Lin, F. L. Lewis, and T. H. Lee, “Local learning enabled iterative linear quadratic regulator for constrained trajectory planning,” IEEE Trans. Neural Netw. Learn. Syst., vol. 34, no. 9, pp. 5354–5365, Sep. 2023.   
[36] C. Hubmann, J. Schulz, M. Becker, D. Althoff, and C. Stiller, “Automated driving in uncertain environments: Planning with interaction and uncertain maneuver prediction,” IEEE Trans. Intell. Vehicles, vol. 3, no. 1, pp. 5–17, Mar. 2018.   
[37] C. Hubmann, N. Quetschlich, J. Schulz, J. Bernhard, D. Althoff, and C. Stiller, “A POMDP maneuver planner for occlusions in urban scenarios,” in Proc. IEEE Intell. Vehicles Symp. (IV), Jun. 2019, pp. 2172–2179.   
[38] C. Tang, Y. Liu, H. Xiao, and L. Xiong, “Integrated decision making and planning framework for autonomous vehicle considering uncertain prediction of surrounding vehicles,” in Proc. IEEE 25th Int. Conf. Intell. Transp. Syst. (ITSC), Oct. 2022, pp. 3867–3872.   
[39] L. Li, W. Zhao, and C. Wang, “POMDP motion planning algorithm based on multi-modal driving intention,” IEEE Trans. Intell. Vehicles, vol. 8, no. 2, pp. 1777–1786, Feb. 2023.   
[40] T. Li, L. Zhang, S. Liu, and S. Shen, “MARC: Multipolicy and riskaware contingency planning for autonomous driving,” IEEE Robot. Autom. Lett., vol. 8, no. 10, pp. 6587–6594, Oct. 2023.   
[41] Y. Chen, U. Rosolia, W. Ubellacker, N. Csomay-Shanklin, and A. D. Ames, “Interactive multi-modal motion planning with branch model predictive control,” IEEE Robot. Autom. Lett., vol. 7, no. 2, pp. 5365–5372, Apr. 2022.

[42] V. K. Adajania, A. Sharma, A. Gupta, H. Masnavi, K. M. Krishna, and A. K. Singh, “Multi-modal model predictive control through batch non-holonomic trajectory optimization: Application to highway driving,” IEEE Robot. Autom. Lett., vol. 7, no. 2, pp. 4220–4227, Apr. 2022.   
[43] Y. Chen, S. Veer, P. Karkus, and M. Pavone, “Interactive joint planning for autonomous vehicles,” IEEE Robot. Autom. Lett., vol. 9, no. 2, pp. 987–994, Feb. 2024.   
[44] O. de Groot, L. Ferranti, D. M. Gavrila, and J. Alonso-Mora, “Topologydriven parallel trajectory optimization in dynamic environments,” 2024, arXiv:2401.06021.   
[45] P. Tseng, “Applications of a splitting algorithm to decomposition in convex programming and variational inequalities,” SIAM J. Control Optim., vol. 29, no. 1, pp. 119–138, Jan. 1991.   
[46] S. Shalev-Shwartz, S. Shammah, and A. Shashua, “On a formal model of safe and scalable self-driving cars,” 2017, arXiv:1708.06374.   
[47] R. T. Farouki, “The Bernstein polynomial basis: A centennial retrospective,” Comput. Aided Geometric Des., vol. 29, no. 6, pp. 379–419, Aug. 2012.   
[48] K. Tong, S. Solmaz, M. Horn, M. Stolz, and D. Watzenig, “Robust tunable trajectory repairing for autonomous vehicles using Bernstein basis polynomials and path-speed decoupling,” in Proc. IEEE 26th Int. Conf. Intell. Transp. Syst. (ITSC), Sep. 2023, pp. 8–15.   
[49] J. Zeng, Z. Li, and K. Sreenath, “Enhancing feasibility and safety of nonlinear model predictive control with discrete-time control barrier functions,” in Proc. 60th IEEE Conf. Decis. Control (CDC), Oct. 2021, pp. 6137–6144.   
[50] F. Rastgar, A. K. Singh, H. Masnavi, K. Kruusamae, and A. Aabloo, “A novel trajectory optimization for affine systems: Beyond convexconcave procedure,” in Proc. IEEE/RSJ Int. Conf. Intell. Robots Syst. (IROS), Oct. 2020, pp. 1308–1315.   
[51] V. K. Adajania, S. Zhou, A. K. Singh, and A. P. Schoellig, “AMSwarm: An alternating minimization approach for safe motion planning of quadrotor swarms in cluttered environments,” in Proc. IEEE Int. Conf. Robot. Autom. (ICRA), May 2023, pp. 1421–1427.   
[52] A. Agrawal and K. Sreenath, “Discrete control barrier functions for safety-critical control of discrete systems with application to bipedal robot navigation,” in Proc. Robot., Sci. Syst. XIII, Cambridge, MA, USA, Jul. 2017, pp. 1–10.   
[53] I. Bae et al., “Self-driving like a human driver instead of a robocar: Personalized comfortable driving experience for autonomous vehicles,” 2020, arXiv:2001.03908.   
[54] L. Biagiotti and C. Melchiorri, Trajectory Planning for Automatic Machines and Robots. Berlin, Germany: Springer, 2008.   
[55] G. Taylor, R. Burmeister, Z. Xu, B. Singh, A. Patel, and T. Goldstein, “Training neural networks without gradients: A scalable ADMM approach,” in Proc. Int. Conf. Mach. Learn., 2016, pp. 2722–2731.   
[56] J. Eckstein, “Parallel alternating direction multiplier decomposition of convex programs,” J. Optim. Theory Appl., vol. 80, no. 1, pp. 39–62, Jan. 1994.   
[57] S. Albeaik et al., “Limitations and improvements of the intelligent driver model (IDM),” SIAM J. Appl. Dyn. Syst., vol. 21, no. 3, pp. 1862–1892, Sep. 2022.   
[58] H. Sha et al., “LanguageMPC: Large language models as decision makers for autonomous driving,” 2023, arXiv:2310.03026.

![](images/e18c1589792958bc5bb4b752b4f9962f2ea56d496145e0b67353e82904d01ef9.jpg)

<details>
<summary>natural_image</summary>

Portrait photo of a young man in formal attire (no text or symbols visible)
</details>

Lei Zheng received the B.Eng. degree in automation from Nanchang University, Nanchang, China, in 2018, and the M.Phil. degree in pattern recognition and intelligent systems from Sun Yat-sen University, Guangzhou, China, in 2021. He is currently pursuing the Ph.D. degree in robotics and autonomous systems with The Hong Kong University of Science and Technology (Guangzhou), Guangzhou. From 2021 to 2022, he was a Senior Robotics Algorithms Engineer with XAG, China. His research interests include optimal control, opti-

mization, motion planning, and nonparametric Bayesian learning with applications to robotics and autonomous driving.

![](images/9289574feeb1b17f70a834f9905f0935f892e37f8a15c9fcfa5f19ad9a68eb78.jpg)

<details>
<summary>natural_image</summary>

Portrait photo of a young man in a white shirt (no text or symbols visible)
</details>

Rui Yang received the B.Eng. degree in intelligence science and technology and the M.Phil. degree in computer science and technology from Sun Yat-sen University, Guangzhou, China, in 2018 and 2021, respectively. He is currently pursuing the Ph.D. degree in robotics and autonomous systems with The Hong Kong University of Science and Technology (Guangzhou), Guangzhou. He was a Robotics Algorithms Engineer with DJI, Shenzhen, China, from 2021 to 2024. His research interests include optimal control, optimization, decision-making, and

machine learning with applications to robotics and autonomous driving.

![](images/179c9873c528923453eade167bf86787887daf71682bf94237564cb420597c45.jpg)

<details>
<summary>natural_image</summary>

Portrait of a man wearing glasses and a collared shirt (no text or symbols visible)
</details>

Michael Yu Wang (Fellow, IEEE) received the B.E. degree in mechanical and manufacturing engineering from Xi’an Jiaotong University, Xi’an, China, in 1982, the M.S. degree in engineering mechanics from The Pennsylvania State University, State College, USA, in 1985, and the Ph.D. degree in mechanical engineering from Carnegie Mellon University, Pittsburgh, USA, in 1989.

He is currently the Dean and a Chair Professor with the School of Engineering, Great Bay University. Before joining Great Bay University in 2024,

he served on the Engineering Faculty, University of Maryland; The Chinese University of Hong Kong; the National University of Singapore; The Hong Kong University of Science and Technology; and Monash University. His research interests include robotic manipulation, learning and autonomous systems, manufacturing automation, and additive manufacturing. He is a fellow of ASME. He was a recipient of the ASME Design Automation Award. He has numerous professional honors, such as the National Science Foundation Research Initiation Award; the Ralph R. Teetor Educational Award from the Society of Automotive Engineers; the LaRoux K. Gillespie Outstanding Young Manufacturing Engineer Award from the Society of Manufacturing Engineers; Boeing–A.D. Welliver Faculty Summer Fellow, Boeing; the Chang Jiang (Cheung Kong) Scholars Award from the Ministry of Education of China and Li Ka Shing Foundation (Hong Kong); and the Research Excellence Award from CUHK. He was the Editor-in-Chief of IEEE TRANSACTIONS ON AUTOMATION SCIENCE AND ENGINEERING.

![](images/941064c34b9b6d49124f4a8979544aa6f47c09fb3d77fa756725c4ac12f8f128.jpg)

<details>
<summary>natural_image</summary>

Portrait photo of a man in a white shirt (no text or symbols visible)
</details>

Jun Ma (Member, IEEE) received the B.Eng. degree with First Class Hons. in electrical and electronic engineering from Nanyang Technological University, Singapore, in 2014, and the Ph.D. degree in electrical and computer engineering from the National University of Singapore, Singapore, in 2018. From 2018 to 2021, he held several positions at the National University of Singapore; University College London, London, U.K.; University of California, Berkeley, Berkeley, CA, USA; and Harvard University, Cambridge, MA, USA. He is currently an Assistant Professor with the Robotics and Autonomous Systems Thrust, The Hong Kong University of Science and Technology (Guangzhou), Guangzhou, China, and the Division of Emerging Interdisciplinary Areas, The Hong Kong University of Science and Technology, Hong Kong SAR, China. He is also the Director of the Intelligent Autonomous Driving Center, The Hong Kong University of Science and Technology (Guangzhou). His research interests include motion planning and control for robotics and autonomous driving.