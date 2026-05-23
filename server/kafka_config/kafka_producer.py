# vaultmind_producer.py
import time
import json
import pandas as pd
from kafka import KafkaProducer

# Initialize Kafka Producer
# Make sure to run: pip install kafka-python pandas
try:
    producer = KafkaProducer(
        bootstrap_servers=['localhost:9092'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        api_version=(2, 5, 0)
    )
    print("[OK] Kafka Producer Connected Successfully!")
except Exception as e:
    print(f"[ERROR] Kafka Connection Failed: {e}")
    exit()

TOPIC_NAME = 'live-transactions'
CSV_FILE = r'D:\DEmo\server\data\Testing_data\live_demo_stream.csv'

def stream_data():
    print(f"[INFO] Starting Live Stream from {CSV_FILE} to Kafka Topic: {TOPIC_NAME}...")
    try:
        # Load the mock dataset
        df = pd.read_csv(CSV_FILE)
        
        for index, row in df.iterrows():
            transaction = row.to_dict()
            
            # Send to Kafka
            producer.send(TOPIC_NAME, transaction)
            print(f"[STREAM] Sent Tx: {transaction.get('transaction_id', 'UNKNOWN')} | Acc: {transaction.get('source_account', 'N/A')}")
            
            # Simulate real-time delay (1.5 seconds per transaction)
            time.sleep(1.5)
            
    except FileNotFoundError:
        print(f"[ERROR] Could not find {CSV_FILE}. Please make sure the dataset exists.")
    except KeyboardInterrupt:
        print("\n[STOP] Streaming Stopped by User.")
    finally:
        producer.close()

if __name__ == "__main__":
    stream_data()