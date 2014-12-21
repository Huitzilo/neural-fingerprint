import numpy as np
from contextlib import contextmanager
from time import time
from functools import partial
import kayak as ky

def slicedict(d, ixs):
    return {k : v[ixs] for k, v in d.iteritems()}

class memoize(object):
    def __init__(self, func):
        self.func = func
        self.cache = {}

    def __call__(self, *args):
        return self.cache.setdefault(args, self.func(*args))

    def __get__(self, obj, objtype):
        return partial(self.__call__, obj)

def normalize_array(A):
    mean, std = np.mean(A), np.std(A)
    A_normed = (A - mean) / std
    def restore_function(X):
        return X * std + mean

    return A_normed, restore_function

@contextmanager
def tictoc():
    print "--- Start clock ---"
    t1 = time()
    yield
    dt = time() - t1
    print "--- Stop clock: %s seconds elapsed ---" % dt

# "Counterfactual value" - helper function to allow testing different inputs
def c_value(output, nodes_and_values):
    for node, new_value in nodes_and_values.iteritems():
        node.value = new_value
    return output.value

def c_grad(ky_function, var, nodes_and_values):
    for node, new_value in nodes_and_values.iteritems():
        node.value = new_value
    return ky_function.grad(var)

class WeightsContainer(object):
    """Container for a collection of weights that camouflages itself as a kayak object."""
    def __init__(self):
        self.N = 0
        self._weights_list = []
        self._names_list = []

    def new(self, shape, name=""):
        w_new = ky.Parameter(np.zeros(shape))
        self._weights_list.append(w_new)
        self.N += np.prod(shape)
        self._names_list.append(name)
        return w_new

    def _d_out_d_self(self, out):
        """Concatenates the gradients of all it contains into a vector,
        so that it can be called by a general-purpose optimizer."""
        grad_list = [out.grad(w) for w in self._weights_list]
        return np.concatenate([arr.ravel() for arr in grad_list])

    @property
    def value(self):
        return np.concatenate([w.val.ravel() for w in self._weights_list])
        
    @value.setter
    def value(self, vect):
        """Re-packages a vector in the original format."""
        for w in self._weights_list:
            sub_vect, vect = np.split(vect, [np.prod(w.shape)])
            w.value = sub_vect.reshape(w.shape)

    def print_shapes(self):
        for weights, name in zip(self._weights_list, self._names_list):
            print name, ":", weights.shape

    def lookup_by_name(self, name):
        # Perhaps it'd be better to replace the two lists with a defaultdict.
        match_ix = [ix for (ix, cur_name) in enumerate(self._names_list) if cur_name is name][0]
        return self._weights_list[match_ix]


class WeightsParser(object):
    """A kind of dictionary of weights shapes,
       which can pick out named subsets from a long vector.
       Does not actually store any weights itself."""
    def __init__(self):
        self.idxs_and_shapes = {}
        self.N = 0

    def add_weights(self, name, shape):
        start = self.N
        self.N += np.prod(shape)
        self.idxs_and_shapes[name] = (slice(start, self.N), shape)

    def get(self, vect, name):
        """Takes in a vector and returns the subset indexed by name."""
        idxs, shape = self.idxs_and_shapes[name]
        return np.reshape(vect[idxs], shape)


