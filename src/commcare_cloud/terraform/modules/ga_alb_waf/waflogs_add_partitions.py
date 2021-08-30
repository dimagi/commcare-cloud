import boto3
import botocore
import io, re, time, os
from datetime import datetime

def check_file(bucket, key):
    s3 = boto3.resource('s3')
    file_exists = False
    try:
        s3bucket = s3.Bucket(bucket)
        #filter with key
        bucket_files = [obj.key for obj in s3bucket.objects.filter(Prefix=key)]
        if any(key in fk for fk in bucket_files):
            file_exists = True
            print("Key is: ",key)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            file_exists = False
        else:
            raise e
    return file_exists


def athena_query(session, params, wait = True):
    client = session.client('athena')
    
    ## This function executes the query and returns the query execution ID
    response_query_execution_id = client.start_query_execution(
        QueryString = params['query'],
        QueryExecutionContext = {
            'Database' : "default"
        }
    )

    if not wait:
        return response_query_execution_id['QueryExecutionId']
    else:
        response_get_query_details = client.get_query_execution(
            QueryExecutionId = response_query_execution_id['QueryExecutionId']
        )
        status = 'RUNNING'
        iterations = 360 # 30 mins

        while (iterations > 0):
            iterations = iterations - 1
            response_get_query_details = client.get_query_execution(
            QueryExecutionId = response_query_execution_id['QueryExecutionId']
            )
            res = response_get_query_details['QueryExecution']
            status = response_get_query_details['QueryExecution']['Status']['State']
            print(status)
            if (status == 'FAILED') or (status == 'CANCELLED') :
                response = response_get_query_details['QueryExecution']['Status']['StateChangeReason']
                return status, response

            elif status == 'SUCCEEDED':
                location = response_get_query_details['QueryExecution']['ResultConfiguration']['OutputLocation']

                ## Function to get output results
                response_query_result = client.get_query_results(
                    QueryExecutionId = response_query_execution_id['QueryExecutionId']
                )
                result_data = response_query_result['ResultSet']

                if len(response_query_result['ResultSet']['Rows']) > 1:
                    header = response_query_result['ResultSet']['Rows'][0]
                    rows = response_query_result['ResultSet']['Rows'][1:]
                    return location, status
                else:
                    return location, "No rows"
            else:
                time.sleep(5)
    return False

def handler(event, context=None, params=None):
    # get UTC date 
    environment = os.environ['environment']
    REGION = os.environ['AWS_REGION']
    utc_datetime = datetime.utcnow()
    year = utc_datetime.strftime('%Y')
    month = utc_datetime.strftime('%m')
    day = utc_datetime.strftime("%d")
    hour = utc_datetime.strftime('%H')

    DATABASE = 'default'
    TABLE = 'waf_logs'

    # S3 constant
    S3_OUTPUT = f"s3://dimagi-commcare-{environment}-logs"
    S3_BUCKET = f"dimagi-commcare-{environment}-logs"
    STREAM_PATH=f"frontend-waf-partitioned-{environment}"
    verifyKey = f"{STREAM_PATH}/year={year}/month={month}/day={day}/hour={hour}"

    addPartitionQuery=f"ALTER TABLE {TABLE} ADD PARTITION (year={year}, month={month}, day={day}, hour={hour}) LOCATION 's3://{S3_BUCKET}/{STREAM_PATH}/year={year}/month={month}/day={day}/hour={hour}/';"
    print(addPartitionQuery)

    params = {
        'region': REGION,
        'database': DATABASE,
        'bucket': S3_BUCKET,
        'path': f'{S3_BUCKET}/{STREAM_PATH}/',
        'query': addPartitionQuery
    }

    session = boto3.Session()
    client = session.client('athena')
    
    key_status = check_file(bucket=S3_BUCKET, key=verifyKey)
    print(key_status)
    if key_status:
        file, response_code = athena_query(session, params)
        print(file, response_code)
