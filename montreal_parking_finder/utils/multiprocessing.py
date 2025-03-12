"""
Multiprocessing utilities for improved performance.
"""

import os
import multiprocessing
from functools import partial
import numpy as np
import pandas as pd
from tqdm import tqdm

from montreal_parking_finder.config import NUM_PROCESSES, BATCH_SIZE


def process_in_parallel(function, items, num_processes=None, batch_size=None, desc=None):
    """
    Process a list of items in parallel using multiple processes.
    
    Args:
        function: Function to apply to each item
        items: List of items to process
        num_processes: Number of processes to use (default: from config)
        batch_size: Size of batches to process (default: from config)
        desc: Description for progress bar
        
    Returns:
        List of results
    """
    if num_processes is None:
        num_processes = NUM_PROCESSES
    
    if batch_size is None:
        batch_size = min(BATCH_SIZE, max(1000, len(items) // (num_processes * 2)))
    
    # Split items into batches
    batches = [items[i:i+batch_size] for i in range(0, len(items), batch_size)]
    
    # Process batches in parallel
    results = []
    with multiprocessing.Pool(processes=num_processes) as pool:
        # Use tqdm for progress tracking if description is provided
        if desc:
            batch_results = list(tqdm(
                pool.imap(function, batches),
                total=len(batches),
                desc=desc
            ))
        else:
            batch_results = pool.map(function, batches)
        
        # Flatten results if needed
        for result in batch_results:
            if isinstance(result, list):
                results.extend(result)
            else:
                results.append(result)
    
    return results


def dataframe_parallel_apply(df, function, axis=1, num_processes=None, batch_size=None, desc=None):
    """
    Apply a function to a DataFrame in parallel.
    
    Args:
        df: DataFrame to process
        function: Function to apply to each row/column
        axis: Apply function to rows (1) or columns (0)
        num_processes: Number of processes to use
        batch_size: Size of batches to process
        desc: Description for progress bar
        
    Returns:
        DataFrame with applied function
    """
    if num_processes is None:
        num_processes = NUM_PROCESSES
    
    if batch_size is None:
        batch_size = min(BATCH_SIZE, max(100, len(df) // (num_processes * 2)))
    
    # Split DataFrame into batches
    df_batches = [df.iloc[i:i+batch_size] for i in range(0, len(df), batch_size)]
    
    # Create a partial function for processing a batch
    def process_batch(batch_df):
        return batch_df.apply(function, axis=axis)
    
    # Process batches in parallel
    with multiprocessing.Pool(processes=num_processes) as pool:
        # Use tqdm for progress tracking if description is provided
        if desc:
            results = list(tqdm(
                pool.imap(process_batch, df_batches),
                total=len(df_batches),
                desc=desc
            ))
        else:
            results = pool.map(process_batch, df_batches)
    
    # Combine results
    return pd.concat(results)


def chunk_reader(file_path, chunk_size=10000, num_processes=None, process_func=None):
    """
    Read and process a large file in chunks with parallel processing.
    
    Args:
        file_path: Path to the CSV file
        chunk_size: Number of rows to read in each chunk
        num_processes: Number of processes to use
        process_func: Function to apply to each chunk
        
    Returns:
        Concatenated result of processed chunks
    """
    if num_processes is None:
        num_processes = min(NUM_PROCESSES, os.cpu_count())
    
    # Set up a pool for parallel processing
    pool = multiprocessing.Pool(processes=num_processes)
    
    # Create a reader for the file
    chunks = pd.read_csv(file_path, chunksize=chunk_size)
    
    # Process each chunk in parallel
    if process_func:
        results = pool.map(process_func, chunks)
    else:
        results = list(chunks)
    
    # Clean up
    pool.close()
    pool.join()
    
    # Combine results
    if results:
        return pd.concat(results, ignore_index=True)
    else:
        return pd.DataFrame()
