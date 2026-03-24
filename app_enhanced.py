import pandas as pd
import gc

# Caching decorator using Streamlit's @st.cache_data
import streamlit as st

@st.cache_data
def load_csv_data(file_path):
    return pd.read_csv(file_path)

@st.cache_data
def load_json_data(file_path):
    return pd.read_json(file_path)

class QueryOptimizer:
    def __init__(self, data):
        self.data = data
        self.cache = {}

    def filtered_query(self, filter_condition):
        if filter_condition in self.cache:
            return self.cache[filter_condition]
        result = self.data.query(filter_condition)
        self.cache[filter_condition] = result
        return result

# Example usage
if __name__ == '__main__':
    csv_data = load_csv_data('data.csv')  # Specify your csv file path
    json_data = load_json_data('data.json')  # Specify your json file path
    
    optimizer = QueryOptimizer(csv_data)
    filtered_data = optimizer.filtered_query('column_name > value')  # Update with your filter condition
    
    # Process data...
    gc.collect()  # Calls garbage collection after processing