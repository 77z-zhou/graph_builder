import os
import time
import uuid
import numpy as np



def normalize_vector(vec):
    vec = np.array(vec, dtype=np.float32)
    norm = np.linalg.norm(vec)
    if norm == 0:
        return vec
    return vec / norm

def generate_id(prefix="id"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def get_timestamp():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

def ensure_directory_exists(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)

def ensure_file_exists(path):
    return os.path.isfile(path)


# ---- Time Decay Function ----


def compute_time_decay(event_timestamp_str, current_timestamp_str, tau_hours=24):
    from datetime import datetime
    fmt = "%Y-%m-%d %H:%M:%S"
    try:
        t_event = datetime.strptime(event_timestamp_str, fmt)
        t_current = datetime.strptime(current_timestamp_str, fmt)
        delta_hours = (t_current - t_event).total_seconds() / 3600.0
        return np.exp(-delta_hours / tau_hours)
    except ValueError: # Handle cases where timestamp might be invalid
        return 0.1 # Default low recency
    

# ------ 计算热力值-----------
# Heat computation constants (can be tuned or made configurable)
HEAT_ALPHA = 1.0
HEAT_BETA = 1.0
HEAT_GAMMA = 1
RECENCY_TAU_HOURS = 24 # For R_recency calculation in compute_segment_heat
def compute_segment_heat(segment, alpha=HEAT_ALPHA, beta=HEAT_BETA, gamma=HEAT_GAMMA, tau_hours=RECENCY_TAU_HOURS):
    N_visit = segment.get("N_visit", 0)
    L_interaction = segment.get("L_interaction", 0)
    
    # Calculate recency based on last_visit_time
    R_recency = 1.0 # Default if no last_visit_time
    if segment.get("last_visit_time"):
        R_recency = compute_time_decay(segment["last_visit_time"], get_timestamp(), tau_hours)
    
    segment["R_recency"] = R_recency # Update session's recency factor
    return alpha * N_visit + beta * L_interaction + gamma * R_recency