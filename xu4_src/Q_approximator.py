import sklearn
from sklearn.neural_network import MLPRegressor as MLPr
import numpy


class QApproximator:
	def __init__(self, num_states, num_actions):
		self.approximators = []
		for a in range(num_actions):
			self.approximators.append( MLPr( solver='sgd' ) )
			self.approximators[-1].fit([[0.0]*num_states],[0.0])
		self.num_actions = num_actions
		self.state_dims = num_states

	def estimate(self, state, action=None):
		if action == None:
			estimates = [0.0] * self.num_actions
			for a in range(self.num_actions):
				estimates[a] = self.approximators[a].predict( [list(state)] )[0]
			return estimates
		else:
			return self.approximators[action].predict( [list(state) + [action]] )
	
	def update(self, state, action, new_value):
		self.approximators[action].fit( [list(state) + [action]], [new_value] )
				
	def getParams(self):
		params = []
		for m in self.approximators:
			params.append(m.get_params())
		return params

	def setParams(self, params):
		if len(self.approximators) != len(params):
			raise Exception("Actionspace sizes do not match.")
		for m,p in zip(self.approximators, params):
			m.set_params(p)
			
			
			
