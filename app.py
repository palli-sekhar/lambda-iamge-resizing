import boto3
from PIL import Image
import io
import os
import urllib.parse
from botocore.exceptions import ClientError

s3 = boto3.client('s3')

SOURCE_BUCKET = "sekhar-so"
DEST_BUCKET = "sekhar-de"

def handler(event, context):
    print("Event:", event)

    try:
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(record['s3']['object']['key'])
        print(f"Decoded key: {key}")

        # Check if the event came from the expected source bucket
        if bucket != SOURCE_BUCKET:
            print(f"Ignoring event from unexpected bucket: {bucket}")
            return {
                'statusCode': 403,
                'body': f"Ignored bucket: {bucket}"
            }

        # Allow only valid image extensions
        if not key.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            print(f"Unsupported file type: {key}")
            return {
                'statusCode': 400,
                'body': f"Unsupported file type: {key}"
            }

        # Fetch the object from source bucket
        try:
            response = s3.get_object(Bucket=bucket, Key=key)
        except ClientError as e:
            if e.response['Error']['Code'] == "NoSuchKey":
                print(f"ERROR: Object not found: {key}")
                return {
                    'statusCode': 404,
                    'body': f"No such key: {key}"
                }
            else:
                raise

        # Resize the image
        image_data = response['Body'].read()
        with Image.open(io.BytesIO(image_data)) as img:
            img = img.resize((200, 200))
            buffer = io.BytesIO()
            save_format = img.format if img.format else 'JPEG'
            img.save(buffer, format=save_format)
            buffer.seek(0)

            # Store to destination bucket under 'resized/' folder
            filename = os.path.basename(key)
            dest_key = f"resized/{filename}"
            s3.put_object(Bucket=DEST_BUCKET, Key=dest_key, Body=buffer, ContentType=response['ContentType'])

        return {
            'statusCode': 200,
            'body': f"Resized image stored at: {DEST_BUCKET}/{dest_key}"
        }

    except Exception as e:
        print("Unhandled error:", str(e))
        return {
            'statusCode': 500,
            'body': f"Internal error: {str(e)}"
        }
