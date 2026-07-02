import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

def plot_memory_leak():
    df = pd.read_csv('tf4-evidence/evidence/holdout_fraud-detector.csv')
    df['ts'] = pd.to_datetime(df['ts'])
    
    fig, ax = plt.subplots(figsize=(12, 5))
    
    # TienThanh's signature color for memory
    color_mem = "#F9A825"
    
    ax.plot(df['ts'], df['memory_usage_percent'], color=color_mem, lw=2, label='memory_usage_percent')
    
    # Highlight the leak region (from index 800 to 980)
    leak_start = df['ts'].iloc[800]
    leak_end = df['ts'].iloc[980]
    
    ax.axvspan(leak_start, leak_end, color='red', alpha=0.1, label='Slow Leak (180 mins)')
    ax.axvline(leak_end, color='red', linestyle='--', lw=1.5, label='Capacity Exhaustion (99%)')
    
    ax.set_title('Silent Exhaustion: fraud-detector Memory Leak (Holdout Scenario)', fontsize=14)
    ax.set_ylabel('Memory Usage (%)', fontsize=11)
    ax.set_xlabel('Time (UTC)', fontsize=11)
    
    ax.set_ylim(0, 100)
    ax.grid(axis='y', alpha=0.3)
    ax.legend(loc='upper left')
    
    fig.tight_layout()
    fig.savefig('tf4-evidence/evidence/scenario_memory_leak.png', dpi=110)
    print("Beautifully updated scenario_memory_leak.png")

if __name__ == "__main__":
    plot_memory_leak()
