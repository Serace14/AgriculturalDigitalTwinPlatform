from temporalio.client import Client
from temporalio.worker import Worker
import asyncio
import os
import logging
from concurrent.futures import ThreadPoolExecutor
from harvest_ai_prediction import HarvestAIPredictionWorkflow, get_data, train_model, predict_yield, load_prediction
from disease_risk.disease_risk_prediction import predict_disease_risk_activity
from disease_risk.disease_risk_workflow import DiseaseRiskWorkflow, get_weather_for_disease_risk

logging.basicConfig(level=logging.INFO)

async def main():
    temporal_uri = os.environ.get("TEMPORAL_ADDRESS", "temporal:7233")
    client = await Client.connect(temporal_uri, namespace="25-56-0-0-13-40-1")
    worker = Worker(client,
                    workflow_task_executor=ThreadPoolExecutor(max_workers=20),
                    task_queue="harvest-ai-prediction-task-queue",
                    workflows=[HarvestAIPredictionWorkflow, DiseaseRiskWorkflow],
                    activities=[get_data, train_model, predict_yield, load_prediction, predict_disease_risk_activity, get_weather_for_disease_risk])
    logging.info("Starting harvest prediction worker")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())