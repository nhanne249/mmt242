import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_bipartite_matching
import os

def max_bipartite_matching_scipy(T, C):
    # Map each item in T to an index
    items = list(T)
    item_index = {item: i for i, item in enumerate(items)}
    
    # Create an adjacency matrix (lists in C as rows, items in T as columns)
    num_lists = len(C)
    num_items = len(T)
    adj_matrix = np.zeros((num_lists, num_items), dtype=int)
    
    # Use gather-like behavior to fill the adjacency matrix
    for i, c_list in enumerate(C):
        # Get indices of the items in c_list from the item_index mapping
        indices = [item_index[item] for item in c_list if item in item_index]
        adj_matrix[i, indices] = 1  # Set to 1 where item exists in the list
    
    # Convert to a sparse matrix format (required by maximum_bipartite_matching)
    sparse_adj_matrix = csr_matrix(adj_matrix)
    
    # Find the maximum bipartite matching
    matching = maximum_bipartite_matching(sparse_adj_matrix, perm_type='column')
    
    # Prepare the result mapping: lists in C to items in T
    result = {}
    for i, item_idx in enumerate(matching):
        if item_idx != -1:
            result[i] = items[item_idx]
    
    return result

# Example usage:
if __name__ == '__main__':
    T = {"S1", "S2", "S3", "S4"}  # Set of items
    C = [["S1", "S2"], ["S1", "S3"], ["S2", "S4"]]  # Lists in C

    result = max_bipartite_matching_scipy(T, C)
    print(result)


def check_file_size(file_name):
    return os.stat(file_name).st_size

def itemgetter(*items):
    def call(obj):
        return tuple(obj[item] for item in items)
    return call
            

