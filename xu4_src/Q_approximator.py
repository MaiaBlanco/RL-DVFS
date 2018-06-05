import sklearn
from sklearn.neural_network import MLPRegressor as MLPr
import numpy as np
import random
from collections import deque

class QApproximator:
	def __init__(self, num_states, num_actions):
	#	self.approximators = []
	#	for a in range(num_actions):
	#		self.approximators.append( MLPr( solver='sgd' ) )
	#		self.approximators[-1].fit([[0.0]*num_states],[0.0])
		self.approximator = MLPr( solver='sgd', hidden_layer_sizes=(50, 30) )
		self.approximator.fit([[0.0]*(num_states+1)],[0.0])
		self.num_actions = num_actions
		self.state_dims = num_states
		self.replay_mem = deque(maxlen=2000)

	def estimate(self, state, action=None):
		if action == None:
			estimates = [0.0] * self.num_actions
			for a in range(self.num_actions):
				estimates[a] = self.approximator.predict( [state + [a] ] )[0]
				#estimates[a] = self.approximators[a].predict( [list(state)] )[0]
			return estimates
		else:
			return self.approximator.predict( [state + [action]] )[0]
	
	def update(self, state, action, new_value):
		self.approximator.fit( [state + [action] ], [new_value] )

# Replay learning per https://keon.io/deep-q-learning/
	def storeExperience(self, state, action, reward, next_state):
		self.replay_mem.append((state, action, reward, next_state))

	def replayExperiences(self, GAMMA, ALPHA, batch_size=32):
		minibatch = random.sample(self.replay_mem, batch_size)
		for state, action, reward, next_state in minibatch:
			inputs = [ next_state + [a] for a in self.num_actions ]
			best_return = reward + GAMMA*np.max(self.approximator.predict( inputs ))
			cur_val = self.approximator.predict( [state + [action]] )[0]
			new_val = cur_val + ALPHA*(best_return - cur_value)
			self.update(state, action, new_val)

	def clearExperience(self):
		self.replay_mem.clear()
#	def getParams(self):
#		params = []
#		for m in self.approximators:
#			params.append(m.get_params())
#		return params
#
#	def setParams(self, params):
#		if len(self.approximators) != len(params):
#			raise Exception("Actionspace sizes do not match.")
#		for m,p in zip(self.approximators, params):
#			m.set_params(p)
			
			
			
