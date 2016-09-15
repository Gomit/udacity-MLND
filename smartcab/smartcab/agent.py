import random
import math
from environment import Agent, Environment
from planner import RoutePlanner
from simulator import Simulator

class LearningAgent(Agent):
    """An agent that learns to drive in the smartcab world."""

    def __init__(self, env, sigmoid_offset=8., sigmoid_rate=0.01, alpha_decay=0.1, gamma=0.5):
        super(LearningAgent, self).__init__(env)  # sets self.env = env, state = None, next_waypoint = None, and a default color
        self.color = 'red'  # override color
        self.planner = RoutePlanner(self.env, self)  # simple route planner to get next_waypoint

        # TODO: Initialize any additional variables here
        self.qtable = {}  # Q-value table: key = state-action, value = Q-value
        self.prev_sa = None  # keep track of previous state-action
        self.global_t = 0.  # keep track of global time, i.e. how many times agent performs update function
        self.net_reward = 0
        self.penalties = 0  # number of times a penalty (reward < 0) was incurred

        # Hyper parameters
        self.INITIAL_Q = 0.
        self.SIGMOID_OFFSET = sigmoid_offset  # Epsilon-greedy exploration: Epsilon = 1 - sigmoid_function
        self.SIGMOID_RATE = sigmoid_rate  # (same as above)
        self.ALPHA_DECAY = alpha_decay  # learning rate: alpha = (global_t + 1)**(-ALPHA_DECAY)
        self.GAMMA = gamma  # discount factor

        #print '%f, %f, %f, %f' % (self.SIGMOID_OFFSET, self.SIGMOID_RATE, self.ALPHA_DECAY, self.GAMMA)  # [debug]

    def reset(self, destination=None):
        self.planner.route_to(destination)
        # TODO: Prepare for a new trip; reset any variables here, if required
        self.net_reward = 0
        self.penalties = 0

    def update(self, t):
        # Gather inputs
        self.next_waypoint = self.planner.next_waypoint()  # from route planner, also displayed by simulator
        inputs = self.env.sense(self)
        deadline = self.env.get_deadline(self)

        # TODO: Update state
        state = (self.next_waypoint, inputs['light'], inputs['oncoming'], inputs['left'], inputs['right'])

        # Update self.state with compressed state, so the GUI can report it
        self.state = self.compress_sa(state, None)[0:4]

        # If Q-value does not exist for current state (any action), make initial Q-value = 0
        valid_actions = [None, 'forward', 'left', 'right']
        for action in valid_actions:
            if self.compress_sa(state, action) not in self.qtable:
                self.qtable[self.compress_sa(state, action)] = self.INITIAL_Q

        # TODO: Select action according to your policy
        # Choose between the following two policies randomly, choosing the random policy with decreasing probability as t increases
        # I.e. Sshifting from "exploration" to "exploitation"
        #   * Random policy (minimum probability of choosing random policy is MIN_RAND_PROB)
        #   * Given our current state, choose the action with maximum Q(state, action) value
        prob_q = 1/(1 + math.exp(-self.SIGMOID_RATE*self.global_t + self.SIGMOID_OFFSET))  # sigmoid function
        threshold = random.uniform(0, 1)

        if prob_q >= threshold:
            qs = [self.qtable[self.compress_sa(state, None)], self.qtable[self.compress_sa(state, 'forward')], self.qtable[self.compress_sa(state, 'left')], self.qtable[self.compress_sa(state, 'right')]]
            action = valid_actions[qs.index(max(qs))]
        else:
            action = random.choice(valid_actions)

        # Execute action and get reward
        reward = self.env.act(self, action)

        # Keep track of net_reward and penalties
        self.net_reward += reward
        if reward < 0:
            self.penalties += 1

        # TODO: Learn policy based on state, action, reward
        sa = self.compress_sa(state, action)
        new_q = reward + self.GAMMA * max([self.qtable[self.compress_sa(state, a)] for a in valid_actions])

        alpha = (self.global_t + 1)**(-self.ALPHA_DECAY)
        self.qtable[sa] = (1 - alpha) * self.qtable[sa] + alpha * new_q

        #print "LearningAgent.update(): deadline = {}, inputs = {}, action = {}, reward = {}".format(deadline, inputs, action, reward)  # [debug]
        #if t%10 == 0:  # [debug]
        #    print 't = ' + str(t); print self.qtable  # [debug]

        # Increment global lifetime of agent
        self.global_t += 1.
        #print 'Global time: %i' % self.global_t  # [debug]

        # Report net_reward and number of penalties
        print 'Net reward: %i, # of penalties: %i' % (self.net_reward, self.penalties)

    def compress_sa(self, state, action):
        """Given state, action pair, compress it into a smaller representation space"""
        # Recall: state = (self.next_waypoint, inputs['light'], inputs['oncoming'], inputs['left'], inputs['right'])
        wp, light, oncoming, left, right = state

        # State compression and internal representation
        # Ignore 'right' altogether, since traffic on the right has no effect on our driving agent
        # Also append our action to the end of list
        sa = [wp, light, oncoming, left, action]

        # Change None to string 'None', so we can use the compressed state+action (tuple) as a hash
        for i in range(len(sa)):
            if sa[i] is None:
                sa[i] = 'None'

        return tuple(sa)

def run():
    """Run the agent for a finite number of trials."""

    # Set up environment and agent
    e = Environment()  # create environment (also adds some dummy traffic)
    a = e.create_agent(LearningAgent)  # create agent
    e.set_primary_agent(a, enforce_deadline=True)  # specify agent to track
    # NOTE: You can set enforce_deadline=False while debugging to allow longer trials

    # Now simulate it
    sim = Simulator(e, update_delay=0.5, display=True)  # create simulator (uses pygame when display=True, if available)
    # NOTE: To speed up simulation, reduce update_delay and/or set display=False

    sim.run(n_trials=100)  # run for a specified number of trials
    # NOTE: To quit midway, press Esc or close pygame window, or hit Ctrl+C on the command-line


if __name__ == '__main__':
    run()