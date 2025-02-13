from workloadrecommender.utils.config import Config
from workloadrecommender.utils.models import WorkloadDetails
from workloadrecommender.read_workload_timeseries import get_workload_agg_timeseries
from workloadrecommender.run_workload_simulation_plan import get_simulation_plans
from workloadrecommender.run_workload_simulation_run import run_simulation_plans
from datetime import datetime, timedelta
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO)

config = Config()
workload_details = WorkloadDetails(
    config=config,
    project_id="gke-rightsize",
    cluster_name="online-boutique",
    location="us-central1-f",
    namespace="default",
    controller_name="recommendationservice",
    controller_type="Deployment",
    container_name="server"
)
# Access dynamically computed properties
print("Initial Total Startup Seconds:", workload_details.total_startup_seconds)
print("Initial Startup Latency Rows:", workload_details.workload_e2e_startup_latency_rows)

# Update scheduled_to_ready_seconds dynamically
workload_details.scheduled_to_ready_seconds = 30.0

# Check updated values
print("\nAfter Update:")
print("Updated Total Startup Seconds:", workload_details.total_startup_seconds)
print("Updated Startup Latency Rows:", workload_details.workload_e2e_startup_latency_rows)


end_datetime=datetime.now()
start_datetime= end_datetime - timedelta(days=1)
workload_df = get_workload_agg_timeseries(config,workload_details,start_datetime,end_datetime)
#workload_df = pd.read_csv("tests/test_files/test_id_6_dataframe.csv")

plans,msg = get_simulation_plans(workload_details, workload_df)


df,recommendation,msg = run_simulation_plans(plans, workload_details, workload_df)
#df.to_csv("df.csv")
#print(recommendation.to_json())


