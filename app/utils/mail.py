import base64
import os
import pickle
import re
import tempfile
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pikepdf
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from app.storage.postgre import executeSQL

# Define the scopes needed for Gmail and Drive access
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/drive.file'
]

temp_files_to_delete = []


def authenticate():
    """Authenticate with Google API and return credentials"""
    creds = None

    # Check if token.pickle file exists with saved credentials
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If no valid credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return creds


def read_unread_emails_and_upload_attachments(drive_folder_id=None, query_filter=None):
    """
    Read unread emails from Gmail, extract information, and upload attachments to Google Drive

    Args:
        drive_folder_id: Optional Google Drive folder ID to upload attachments to
                        (if None, uploads to root of My Drive)
        query_filter: Optional Gmail query string to filter emails
                     (combined with 'is:unread')
                     See Gmail search operators: 
                     https://support.google.com/mail/answer/7190

    Returns:
        List of dictionaries with email details including attachment upload info
    """
    # Authenticate with Google
    creds = authenticate()

    # Build Gmail and Drive services
    gmail_service = build('gmail', 'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)

    # Build the search query - always include 'is:unread'
    search_query = 'is:unread'
    if query_filter:
        search_query = f"{search_query} {query_filter}"

    # Get list of unread messages
    results = gmail_service.users().messages().list(
        userId='me',
        q=search_query
    ).execute()

    messages = results.get('messages', [])

    if not messages:
        print(f"No unread messages found matching query: '{search_query}'")
        return []

    email_list = []

    # Process each unread email
    for message in messages:
        msg_id = message['id']

        # Get the message details
        msg = gmail_service.users().messages().get(
            userId='me',
            id=msg_id,
            format='full'
        ).execute()

        # Extract headers
        headers = msg['payload']['headers']
        email_data = {
            'message_id': msg_id,
            'smtp_message_id': '',
            'subject': '',
            'from': '',
            'from_email': '',
            'to': '',
            'cc': '',
            'date': '',
            'attachments': [],
            'body': ''
        }
        # Process headers
        for header in headers:
            name = header['name'].lower()
            print("header", header)
            if name == 'subject':
                email_data['subject'] = header['value']
            elif name == 'from':
                # Store the full "From" value
                full_from = header['value']
                email_data['from'] = full_from

                # Extract just the email address using regex
                email_match = re.search(r'<([^>]+)>', full_from)
                if email_match:
                    # If email is in angle brackets like: "Name <email@example.com>"
                    email_data['from_email'] = email_match.group(1)
                else:
                    # If there are no angle brackets, assume the whole string is the email
                    email_data['from_email'] = full_from
            elif name == 'to':
                email_data['to'] = header['value']
            elif name == 'cc':
                email_data['cc'] = header['value']
            elif name == 'date':
                email_data['date'] = header['value']
            elif name == 'message-id':  # Add this condition to extract Message-ID
                email_data['smtp_message_id'] = header['value']

        # Process parts (body and attachments)
        process_parts(
            gmail_service,
            drive_service,
            drive_folder_id,
            msg['payload'],
            email_data
        )

        # Mark the message as read
        gmail_service.users().messages().modify(
            userId='me',
            id=msg_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()

        email_list.append(email_data)

    return email_list


def send_email_with_attachments(subject, body, to_emails, cc_emails=None, bcc_emails=None,
                                attachment_paths=None, drive_file_ids=None, base64_attachments=None):
    """
    Send an email with attachments using Gmail API

    Args:
        subject: Email subject
        body: Email body text
        to_emails: List of recipient email addresses or string for a single recipient
        cc_emails: List of CC email addresses or string for a single CC recipient (optional)
        bcc_emails: List of BCC email addresses or string for a single BCC recipient (optional)
        attachment_paths: List of file paths to attach (optional)
        drive_file_ids: List of Google Drive file IDs to attach (optional)
        base64_attachments: List of dicts with {'filename', 'data', 'mime_type'} for base64 encoded files (optional)
                            - filename: Name to use for the attachment
                            - data: Base64 encoded string of the file content
                            - mime_type: MIME type of the file (e.g., 'application/pdf')

    Returns:
        Dictionary with 'success' boolean and 'message_id' if successful
    """
    # Authenticate with Google
    creds = authenticate()
    gmail_service = build('gmail', 'v1', credentials=creds)

    # Initialize drive service if we have drive file IDs
    drive_service = None
    if drive_file_ids:
        drive_service = build('drive', 'v3', credentials=creds)

    # Create message container
    message = MIMEMultipart()
    message['Subject'] = subject

    # Handle recipients
    if isinstance(to_emails, str):
        message['To'] = to_emails
    else:
        message['To'] = ', '.join(to_emails)

    # Handle CC recipients if provided
    if cc_emails:
        if isinstance(cc_emails, str):
            message['Cc'] = cc_emails
        else:
            message['Cc'] = ', '.join(cc_emails)

    # Handle BCC recipients if provided - Note: BCC won't appear in the message headers
    bcc_list = []
    if bcc_emails:
        if isinstance(bcc_emails, str):
            bcc_list = [bcc_emails]
        else:
            bcc_list = bcc_emails

    # Add body
    # message.attach(MIMEText(body, 'plain'))
    message.attach(MIMEText(body, 'html'))

    # Process local file attachments
    temp_files_to_cleanup = []

    try:
        # Add attachments from local files
        if attachment_paths:
            for file_path in attachment_paths:
                try:
                    with open(file_path, 'rb') as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())

                    # Encode file in ASCII characters to send by email
                    encoders.encode_base64(part)

                    # Add header as key/value pair to attachment part
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {os.path.basename(file_path)}',
                    )

                    message.attach(part)
                except Exception as e:
                    print(f"Error attaching file {file_path}: {e}")

        # Process Google Drive file attachments
        if drive_file_ids and drive_service:
            for file_id in drive_file_ids:
                try:
                    # Get file metadata
                    file_metadata = drive_service.files().get(
                        fileId=file_id, fields='name,mimeType').execute()
                    file_name = file_metadata.get(
                        'name', f'attachment_{file_id}')

                    # Download the file to a temporary location
                    request = drive_service.files().get_media(fileId=file_id)

                    # Create a temporary file
                    temp_file = tempfile.NamedTemporaryFile(delete=False)
                    temp_path = temp_file.name
                    temp_files_to_cleanup.append(temp_path)

                    # Download to the temporary file
                    downloader = MediaIoBaseDownload(temp_file, request)
                    done = False
                    while done is False:
                        _, done = downloader.next_chunk()

                    temp_file.close()

                    # Attach the downloaded file
                    with open(temp_path, 'rb') as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())

                    # Encode file
                    encoders.encode_base64(part)

                    # Add header
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {file_name}',
                    )

                    message.attach(part)

                except Exception as e:
                    print(f"Error attaching Drive file {file_id}: {e}")

        # Process base64 encoded file attachments
        if base64_attachments:
            for attachment_info in base64_attachments:
                try:
                    # Extract information from the attachment info dictionary
                    filename = attachment_info.get(
                        'filename', 'attachment.bin')
                    mime_type = attachment_info.get(
                        'mime_type', 'application/octet-stream')
                    base64_data = attachment_info.get('data', '')

                    if not base64_data:
                        print(
                            f"Error attaching base64 file {filename}: No data provided")
                        continue

                    # Decode the base64 data
                    try:
                        file_data = base64.b64decode(base64_data)
                    except Exception as e:
                        print(
                            f"Error decoding base64 data for {filename}: {e}")
                        continue

                    # Create attachment part
                    main_type, sub_type = mime_type.split(
                        '/', 1) if '/' in mime_type else (mime_type, '')
                    part = MIMEBase(main_type, sub_type)
                    part.set_payload(file_data)

                    # Encode in ASCII to send by email
                    encoders.encode_base64(part)

                    # Add header
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {filename}',
                    )

                    message.attach(part)

                except Exception as e:
                    print(
                        f"Error attaching base64 file {attachment_info.get('filename', 'unknown')}: {e}")

        # Convert to string and encode in base64 for Gmail API
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        # Create the message body
        gmail_message = {
            'raw': encoded_message
        }

        # Send the message
        sent_message = gmail_service.users().messages().send(
            userId='me',
            body=gmail_message
        ).execute()

        return {
            'success': True,
            'message_id': sent_message['id'],
            'thread_id': sent_message.get('threadId')
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
    finally:
        # Clean up any temporary files
        for temp_file in temp_files_to_cleanup:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception:
                pass


def process_parts(gmail_service, drive_service, drive_folder_id, part, email_data, prefix=''):
    """Recursively process message parts for body and attachments"""

    # Check if this part has parts (multipart message)
    if 'parts' in part:
        for i, subpart in enumerate(part['parts']):
            process_parts(gmail_service, drive_service, drive_folder_id,
                          subpart, email_data, f"{prefix}.{i}" if prefix else f"{i}")
    else:
        # Process the part based on its MIME type
        mime_type = part.get('mimeType', '')

        # Handle body content (text/plain or text/html)
        if mime_type == 'text/plain' and not email_data['body']:
            data = part.get('body', {}).get('data', '')
            if data:
                decoded_data = base64.urlsafe_b64decode(data).decode('utf-8')
                email_data['body'] = decoded_data

        # Handle attachments
        if 'filename' in part and part['filename']:
            # Check if it's a PDF file based on extension
            file_name = part['filename'].lower()
            if not file_name.endswith('.pdf'):
                # Skip non-PDF files
                return

            attachment = {
                'filename': part['filename'],
                'mimeType': mime_type,
                'part_id': part['partId'] if 'partId' in part else prefix,
                'size': part['body'].get('size', 0) if 'body' in part else 0
            }

            # Download the attachment
            if 'attachmentId' in part['body']:
                attachment_id = part['body']['attachmentId']
                attachment_data = gmail_service.users().messages().attachments().get(
                    userId='me',
                    messageId=email_data['message_id'],
                    id=attachment_id
                ).execute()

                # Save the attachment to a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{part['filename']}") as tmp_file:
                    file_data = base64.urlsafe_b64decode(
                        attachment_data['data'])
                    tmp_file.write(file_data)
                    temp_path = tmp_file.name

                # Validate if it's a genuine PDF file
                if not is_valid_pdf(temp_path):
                    attachment['upload_error'] = f"Invalid PDF format {part['filename']}"
                    email_data['attachments'].append(attachment)

                    # Add the file to cleanup list but don't upload it
                    if temp_path and os.path.exists(temp_path):
                        temp_files_to_delete.append(temp_path)
                    return

                # Upload the attachment to Google Drive
                try:
                    file_metadata = {
                        'name': part['filename'],
                    }
                    if drive_folder_id:
                        file_metadata['parents'] = [drive_folder_id]

                    media = MediaFileUpload(
                        temp_path,
                        mimetype='application/pdf',  # Force PDF mime type
                        resumable=True
                    )

                    drive_file = drive_service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields='id, webViewLink, webContentLink'  # Added webContentLink
                    ).execute()

                    attachment['drive_file_id'] = drive_file.get('id')
                    attachment['drive_view_link'] = drive_file.get(
                        'webViewLink')
                    attachment['drive_download_link'] = drive_file.get(
                        'webContentLink')

                    # Set file permissions to make it accessible
                    permission = {
                        'type': 'anyone',
                        'role': 'reader',  # 'reader' allows viewing/downloading
                    }

                    drive_service.permissions().create(
                        fileId=drive_file.get('id'),
                        body=permission,
                        fields='id',
                    ).execute()

                    # Insert to database
                    sql = "INSERT INTO email_contents (sender, cc, file_name, link, original_message_id,status) VALUES (%s, %s, %s, %s, %s,%s)"
                    params = (email_data['from_email'], email_data['cc'],
                              part['filename'], attachment['drive_file_id'], email_data['message_id'], 'CHUA_XU_LY')
                    executeSQL(sql, params)

                except Exception as e:
                    attachment['upload_error'] = str(e)

                finally:
                    # Clean up the temporary file
                    if temp_path and os.path.exists(temp_path):
                        temp_files_to_delete.append(temp_path)

            email_data['attachments'].append(attachment)


def reply_to_email(original_message_id, body, to_emails=None, cc_emails=None, bcc_emails=None,
                   attachment_paths=None, drive_file_ids=None, base64_attachments=None,
                   include_original_content=False):
    """
    Reply to an email using Gmail API

    Args:
        original_message_id: ID of the message being replied to
        body: Email body text for the reply
        to_emails: List of recipient email addresses or string for a single recipient (optional, 
                  if None will reply to the original sender)
        cc_emails: List of CC email addresses or string for a single CC recipient (optional)
        bcc_emails: List of BCC email addresses or string for a single BCC recipient (optional)
        attachment_paths: List of file paths to attach (optional)
        drive_file_ids: List of Google Drive file IDs to attach (optional)
        base64_attachments: List of dicts with {'filename', 'data', 'mime_type'} for base64 encoded files (optional)
        include_original_content: Whether to include the original email content in the reply (optional)

    Returns:
        Dictionary with 'success' boolean and 'message_id' if successful
    """
    # Authenticate with Google
    creds = authenticate()
    gmail_service = build('gmail', 'v1', credentials=creds)

    temp_files_to_cleanup = []
    # Initialize drive service if we have drive file IDs
    drive_service = None
    if drive_file_ids:
        drive_service = build('drive', 'v3', credentials=creds)

    try:
        # Fetch the original message to get thread ID and other details
        original_message = gmail_service.users().messages().get(
            userId='me',
            id=original_message_id,
            format='metadata',
            metadataHeaders=['Subject', 'From', 'To', 'Cc',
                             'Message-ID', 'References', 'In-Reply-To']
        ).execute()

        thread_id = original_message.get('threadId')

        # Extract headers from original message
        headers = original_message.get('payload', {}).get('headers', [])
        original_subject = ''
        original_from = ''
        original_to = ''
        original_cc = ''
        original_message_id_header = ''
        original_references = ''

        for header in headers:
            name = header.get('name', '').lower()
            if name == 'subject':
                original_subject = header.get('value', '')
            elif name == 'from':
                original_from = header.get('value', '')
            elif name == 'to':
                original_to = header.get('value', '')
            elif name == 'cc':
                original_cc = header.get('value', '')
            elif name == 'message-id':
                original_message_id_header = header.get('value', '')
            elif name == 'references':
                original_references = header.get('value', '')

        # Extract email from the "From" field using regex
        from_email = ''
        email_match = re.search(r'<([^>]+)>', original_from)
        if email_match:
            from_email = email_match.group(1)
        else:
            from_email = original_from

        # Create message container
        message = MIMEMultipart()

        # Set subject (ensuring it has "Re:" prefix if not already there)
        if original_subject.lower().startswith('re:'):
            message['Subject'] = original_subject
        else:
            message['Subject'] = f"Re: {original_subject}"

        # Set recipients
        if to_emails is None:
            # Reply to the original sender if to_emails is not provided
            message['To'] = from_email
        else:
            # Use provided recipients
            if isinstance(to_emails, str):
                message['To'] = to_emails
            else:
                message['To'] = ', '.join(to_emails)

        # Handle CC recipients if provided
        if cc_emails:
            if isinstance(cc_emails, str):
                message['Cc'] = cc_emails
            else:
                message['Cc'] = ', '.join(cc_emails)

        # Handle BCC recipients if provided - Note: BCC won't appear in the message headers
        bcc_list = []
        if bcc_emails:
            if isinstance(bcc_emails, str):
                bcc_list = [bcc_emails]
            else:
                bcc_list = bcc_emails

        # Set headers for proper threading
        if original_message_id_header:
            message['In-Reply-To'] = original_message_id_header

            # Set References header for threading
            new_references = original_message_id_header
            if original_references:
                new_references = f"{original_references} {original_message_id_header}"
            message['References'] = new_references

        # Create the reply body
        reply_body = body

        # Include original content if requested
        if include_original_content:
            # Get the original message content
            full_message = gmail_service.users().messages().get(
                userId='me',
                id=original_message_id,
                format='full'
            ).execute()

            # Extract original message text
            original_text = extract_text_from_message(
                gmail_service, full_message)

            # Format with quote prefix
            quoted_text = '\n'.join(
                [f"> {line}" for line in original_text.split('\n')])

            # Combine new reply with original quoted text
            reply_body = f"{body}\n\nOn {original_message.get('internalDate', '')}, {original_from} wrote:\n{quoted_text}"

        # Add body
        message.attach(MIMEText(reply_body, 'plain'))

        # Process local file attachments

        # The attachment handling code is identical to send_email_with_attachments
        if attachment_paths:
            for file_path in attachment_paths:
                try:
                    with open(file_path, 'rb') as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())

                    # Encode file in ASCII characters to send by email
                    encoders.encode_base64(part)

                    # Add header as key/value pair to attachment part
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {os.path.basename(file_path)}',
                    )

                    message.attach(part)
                except Exception as e:
                    print(f"Error attaching file {file_path}: {e}")

        # Process Google Drive file attachments
        if drive_file_ids and drive_service:
            for file_id in drive_file_ids:
                try:
                    # Get file metadata
                    file_metadata = drive_service.files().get(
                        fileId=file_id, fields='name,mimeType').execute()
                    file_name = file_metadata.get(
                        'name', f'attachment_{file_id}')

                    # Download the file to a temporary location
                    request = drive_service.files().get_media(fileId=file_id)

                    # Create a temporary file
                    temp_file = tempfile.NamedTemporaryFile(delete=False)
                    temp_path = temp_file.name
                    temp_files_to_cleanup.append(temp_path)

                    # Download to the temporary file
                    downloader = MediaIoBaseDownload(temp_file, request)
                    done = False
                    while done is False:
                        _, done = downloader.next_chunk()

                    temp_file.close()

                    # Attach the downloaded file
                    with open(temp_path, 'rb') as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())

                    # Encode file
                    encoders.encode_base64(part)

                    # Add header
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {file_name}',
                    )

                    message.attach(part)

                except Exception as e:
                    print(f"Error attaching Drive file {file_id}: {e}")

        # Process base64 encoded file attachments
        if base64_attachments:
            for attachment_info in base64_attachments:
                try:
                    # Extract information from the attachment info dictionary
                    filename = attachment_info.get(
                        'filename', 'attachment.bin')
                    mime_type = attachment_info.get(
                        'mime_type', 'application/octet-stream')
                    base64_data = attachment_info.get('data', '')

                    if not base64_data:
                        print(
                            f"Error attaching base64 file {filename}: No data provided")
                        continue

                    # Decode the base64 data
                    try:
                        file_data = base64.b64decode(base64_data)
                    except Exception as e:
                        print(
                            f"Error decoding base64 data for {filename}: {e}")
                        continue

                    # Create attachment part
                    main_type, sub_type = mime_type.split(
                        '/', 1) if '/' in mime_type else (mime_type, '')
                    part = MIMEBase(main_type, sub_type)
                    part.set_payload(file_data)

                    # Encode in ASCII to send by email
                    encoders.encode_base64(part)

                    # Add header
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {filename}',
                    )

                    message.attach(part)

                except Exception as e:
                    print(
                        f"Error attaching base64 file {attachment_info.get('filename', 'unknown')}: {e}")

        # Convert to string and encode in base64 for Gmail API
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        # Create the message body
        gmail_message = {
            'raw': encoded_message,
            'threadId': thread_id  # Include threadId to ensure it's added to the existing thread
        }

        # Send the message
        sent_message = gmail_service.users().messages().send(
            userId='me',
            body=gmail_message
        ).execute()

        return {
            'success': True,
            'message_id': sent_message['id'],
            'thread_id': sent_message.get('threadId')
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
    finally:
        # Clean up any temporary files
        for temp_file in temp_files_to_cleanup:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception:
                pass


def extract_text_from_message(gmail_service, message):
    """Extract plain text from a Gmail message"""
    if 'payload' not in message:
        return ""

    return extract_text_from_part(gmail_service, message['payload'], message.get('id', ''))


def extract_text_from_part(gmail_service, part, message_id):
    """Recursively extract text from message parts"""
    if 'parts' in part:
        # Multipart message - recursively process parts
        text_parts = []
        for subpart in part['parts']:
            text_parts.append(extract_text_from_part(
                gmail_service, subpart, message_id))
        return "\n".join([t for t in text_parts if t])

    # Check if this is a text part
    mime_type = part.get('mimeType', '')
    if mime_type == 'text/plain':
        # Get the body content
        body = part.get('body', {})
        if 'data' in body:
            # Data is directly in the message
            data = body.get('data', '')
            if data:
                return base64.urlsafe_b64decode(data).decode('utf-8')
        elif 'attachmentId' in body:
            # Need to fetch the attachment
            attachment_id = body['attachmentId']
            attachment = gmail_service.users().messages().attachments().get(
                userId='me',
                messageId=message_id,
                id=attachment_id
            ).execute()
            data = attachment.get('data', '')
            if data:
                return base64.urlsafe_b64decode(data).decode('utf-8')

    return ""


def is_valid_pdf(file_path):
    """
    Check if a file is a valid PDF using pikepdf

    Args:
        file_path: Path to the file to check

    Returns:
        Boolean indicating if the file is a valid PDF
    """
    try:
        # Basic header check first (quick rejection)
        with open(file_path, 'rb') as f:
            if not f.read(4).startswith(b'%PDF'):
                print("Invalid PDF header")
                return False

        # Full structure validation with pikepdf
        with pikepdf.open(file_path) as pdf:
            # Check PDF version - convert to float for comparison
            try:
                pdf_version = float(str(pdf.pdf_version))
                if pdf_version < 1.0 or pdf_version > 2.0:
                    print(f"Unusual PDF version: {pdf_version}")
                    return False
            except (ValueError, TypeError):
                # If conversion fails, log but don't reject the PDF just for this
                print(f"Could not validate PDF version: {pdf.pdf_version}")

            # Access document catalog and pages
            _ = pdf.Root
            num_pages = len(pdf.pages)

            # Check if there's at least one page
            if num_pages == 0:
                print("PDF has no pages")
                return False

            # Try to access first page content (checks document structure)
            try:
                _ = pdf.pages[0].Contents
            except Exception as e:
                print(f"Error accessing page contents: {e}")
                return False

            return True

    except pikepdf.PdfError as e:
        print(f"PDF validation failed: {e}")
        return False
    except Exception as e:
        print(f"Error validating PDF: {e}")
        return False


def cleanup_temp_files():
    for file_path in temp_files_to_delete:
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"Warning: Could not delete temporary file {file_path}: {e}")


def download_drive_file(file_id, return_type="both"):
    """
    Downloads a file from Google Drive and returns its base64 encoded content and/or temp file path

    Args:
        file_id: Google Drive file ID to download
        return_type: What to return - "both" (default), "temp_file", or "base64"

    Returns:
        Dictionary containing:
        - success: Boolean indicating if the download was successful
        - base64_data: Base64 encoded string of the file content (if return_type is "both" or "base64")
        - temp_path: Path to the temporary file where the file is saved (if return_type is "both" or "temp_file")
        - mime_type: MIME type of the file (always returned if successful)
        - file_name: Original filename from Google Drive (always returned if successful)
        - error: Error message (if unsuccessful)
    """
    # Authenticate with Google
    creds = authenticate()
    drive_service = build('drive', 'v3', credentials=creds)

    try:
        # Get file metadata to get the name and mime type
        file_metadata = drive_service.files().get(
            fileId=file_id,
            fields='name,mimeType'
        ).execute()

        file_name = file_metadata.get('name', f'file_{file_id}')
        mime_type = file_metadata.get('mimeType', 'application/octet-stream')

        # Extract file extension from the original filename
        _, file_extension = os.path.splitext(file_name)
        if not file_extension:
            # If no extension, try to get one from mime type
            if mime_type == 'application/pdf':
                file_extension = '.pdf'
            elif mime_type == 'image/jpeg':
                file_extension = '.jpg'
            elif mime_type == 'image/png':
                file_extension = '.png'
            # Add more mime types as needed

        # Download the file to a temporary location with the correct extension
        request = drive_service.files().get_media(fileId=file_id)

        # Create temporary file with the original extension
        fd, temp_path = tempfile.mkstemp(suffix=file_extension)

        # Convert file descriptor to file object
        temp_file = os.fdopen(fd, 'wb')

        # Add to cleanup list for later deletion
        temp_files_to_delete.append(temp_path)

        # Download to the temporary file
        downloader = MediaIoBaseDownload(temp_file, request)
        done = False
        while done is False:
            _, done = downloader.next_chunk()

        temp_file.close()

        result = {
            'success': True,
            'mime_type': mime_type,
            'file_name': file_name
        }

        # Include temp_path if requested
        if return_type in ["both", "temp_file"]:
            result['temp_path'] = temp_path

        # Include base64 data if requested
        if return_type in ["both", "base64"]:
            with open(temp_path, 'rb') as file:
                file_content = file.read()
                result['base64_data'] = base64.b64encode(
                    file_content).decode('utf-8')

        return result

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


# Example usage
""" if __name__ == "__main__":
    # Optional: Specify a Google Drive folder ID to upload attachments to
    # If not specified, attachments will be uploaded to the root of My Drive
    drive_folder_id = None  # Replace with your folder ID if needed

    emails = read_unread_emails_and_upload_attachments(drive_folder_id)

    # Print results
    print(f"Found {len(emails)} unread emails:")
    for i, email in enumerate(emails):
        print(f"\nEmail {i+1}:")
        print(f"From: {email['from']}")
        print(f"To: {email['to']}")
        if email['cc']:
            print(f"CC: {email['cc']}")
        print(f"Subject: {email['subject']}")
        print(f"Date: {email['date']}")
        print(f"Attachments: {len(email['attachments'])}")

        for attachment in email['attachments']:
            print(f"  - {attachment['filename']} ({attachment['mimeType']})")
            if 'drive_file_id' in attachment:
                print(f"    File ID: {attachment['drive_file_id']}")
                print(f"    View Link: {attachment['drive_view_link']}")
                if 'drive_download_link' in attachment:
                    print(
                        f"    Download Link: {attachment['drive_download_link']}")
            elif 'upload_error' in attachment:
                print(f"    Upload failed: {attachment['upload_error']}")

        print(f"Body: {email['body'][:100]}..." if email['body']
              else "No text body found")

    cleanup_temp_files()

    send_email_with_attachments(
        subject="Mixed Attachments",
        body="Here are files you asked about",
        to_emails="longnt@hpt.vn",
        drive_file_ids=["1FZY2HHBH3kHtPAVZcOPlmq_oE0gl0KzS"]
    ) """
