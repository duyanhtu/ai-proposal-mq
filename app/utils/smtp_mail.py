import email
import imaplib
import os
import re
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from pathlib import Path
from typing import Any, Dict, List, Union


class GmailSMTPClient:
    """
    A class for sending and reading emails via Gmail using SMTP and IMAP protocols.
    This allows direct interaction with Gmail without requiring the Gmail API.
    """

    def __init__(self, email_address: str, password: str, smtp_host: str = "smtp.gmail.com",
                 smtp_port: int = 587, imap_host: str = "imap.gmail.com", imap_port: int = 993):
        """
        Initialize the Gmail client with credentials and server information.

        Args:
            email_address: Gmail email address
            password: Gmail password or app password (recommended for 2FA enabled accounts)
            smtp_host: SMTP server host (default: smtp.gmail.com)
            smtp_port: SMTP server port (default: 587)
            imap_host: IMAP server host (default: imap.gmail.com)
            imap_port: IMAP server port (default: 993)
        """
        self.email_address = email_address
        self.password = password
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.imap_host = imap_host
        self.imap_port = imap_port

    def send_email(self, to_emails: Union[str, List[str]], subject: str, body: str,
                   cc_emails: Union[str, List[str]] = None, bcc_emails: Union[str, List[str]] = None,
                   attachment_paths: List[str] = None, html_content: str = None) -> Dict[str, Any]:
        """
        Send an email with optional attachments.

        Args:
            to_emails: Recipient email address(es)
            subject: Email subject
            body: Plain text email body
            cc_emails: CC recipient email address(es)
            bcc_emails: BCC recipient email address(es)
            attachment_paths: List of file paths to attach
            html_content: HTML version of the email body (optional)

        Returns:
            Dict with status and error message if any
        """
        # Create message container
        message = MIMEMultipart('alternative')
        message['From'] = self.email_address
        message['Subject'] = subject
        message['Date'] = formatdate(localtime=True)

        # Handle recipients
        if isinstance(to_emails, str):
            message['To'] = to_emails
            to_list = [to_emails]
        else:
            message['To'] = ', '.join(to_emails)
            to_list = to_emails

        # Handle CC recipients
        cc_list = []
        if cc_emails:
            if isinstance(cc_emails, str):
                message['Cc'] = cc_emails
                cc_list = [cc_emails]
            else:
                message['Cc'] = ', '.join(cc_emails)
                cc_list = cc_emails

        # Handle BCC recipients
        bcc_list = []
        if bcc_emails:
            if isinstance(bcc_emails, str):
                bcc_list = [bcc_emails]
            else:
                bcc_list = bcc_emails

        # Create list of all recipients for sending
        all_recipients = to_list + cc_list + bcc_list

        # Add plain text body
        part1 = MIMEText(body, 'plain')
        message.attach(part1)

        # Add HTML version if provided
        if html_content:
            part2 = MIMEText(html_content, 'html')
            message.attach(part2)

        # Process attachments
        if attachment_paths:
            for file_path in attachment_paths:
                try:
                    # Check if file exists
                    if not os.path.isfile(file_path):
                        continue

                    # Get filename from path
                    filename = Path(file_path).name

                    # Open file in binary mode
                    with open(file_path, 'rb') as attachment:
                        # Add file as application/octet-stream
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())

                    # Encode file in ASCII characters to send by email
                    encoders.encode_base64(part)

                    # Add header with filename
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {filename}',
                    )

                    # Add attachment to message
                    message.attach(part)
                except Exception as e:
                    return {'success': False, 'error': f"Error attaching file {file_path}: {str(e)}"}

        try:
            # Connect to server
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()  # Secure the connection
                server.login(self.email_address, self.password)

                # Send email
                server.sendmail(self.email_address,
                                all_recipients, message.as_string())

            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def reply_to_email(self, original_message_id: str, body: str,
                       include_original_content: bool = False,
                       to_emails: Union[str, List[str]] = None,
                       cc_emails: Union[str, List[str]] = None,
                       bcc_emails: Union[str, List[str]] = None,
                       attachment_paths: List[str] = None) -> Dict[str, Any]:
        """
        Reply to an existing email thread.

        Args:
            original_message_id: Message ID of the original email
            body: Reply body text
            include_original_content: Whether to include the original email content in the reply
            to_emails: Override recipient email address(es)
            cc_emails: CC recipient email address(es)
            bcc_emails: BCC recipient email address(es)
            attachment_paths: List of file paths to attach

        Returns:
            Dict with status and error message if any
        """
        try:
            # Connect to IMAP server to fetch original message
            with imaplib.IMAP4_SSL(self.imap_host, self.imap_port) as imap:
                imap.login(self.email_address, self.password)
                imap.select('INBOX')

                # Search for the message by Message-ID
                status, messages = imap.search(
                    None, f'HEADER Message-ID "{original_message_id}"')
                if status != 'OK' or not messages[0]:
                    # If not found by Message-ID, try searching by internal ID
                    try:
                        status, messages = imap.fetch(
                            original_message_id, '(RFC822)')
                    except:
                        return {'success': False, 'error': f"Original message with ID {original_message_id} not found"}

                # Get the message
                if status == 'OK' and messages[0]:
                    if isinstance(messages[0], tuple):
                        # If using fetch by ID
                        email_data = messages[0][1]
                    else:
                        # If using search by Message-ID
                        msg_num = messages[0].split()[0]
                        status, email_data = imap.fetch(msg_num, '(RFC822)')
                        email_data = email_data[0][1]

                    # Parse the email
                    original_email = email.message_from_bytes(email_data)

                    # Extract headers from original email
                    original_subject = original_email['Subject'] or ''
                    original_from = original_email['From'] or ''
                    original_message_id_header = original_email['Message-ID'] or ''
                    original_references = original_email['References'] or ''

                    # Extract email address from From field
                    from_email = ''
                    email_match = re.search(r'<([^>]+)>', original_from)
                    if email_match:
                        from_email = email_match.group(1)
                    else:
                        from_email = original_from

                    # Prepare subject with Re: prefix if needed
                    if original_subject.lower().startswith('re:'):
                        reply_subject = original_subject
                    else:
                        reply_subject = f"Re: {original_subject}"

                    # Extract plain text content from original email
                    original_text = ""
                    if include_original_content:
                        for part in original_email.walk():
                            if part.get_content_type() == 'text/plain':
                                try:
                                    original_text = part.get_payload(
                                        decode=True).decode('utf-8')
                                    break
                                except:
                                    pass

                    # Format quoted text with > prefix
                    if original_text:
                        quoted_text = '\n'.join(
                            [f"> {line}" for line in original_text.split('\n')])
                        reply_body = f"{body}\n\nOn {original_email['Date']}, {original_from} wrote:\n{quoted_text}"
                    else:
                        reply_body = body

                    # Determine recipients
                    if to_emails is None:
                        # Reply to the original sender if to_emails is not provided
                        reply_to = from_email
                    else:
                        reply_to = to_emails

                    # Send the reply
                    result = self.send_email(
                        to_emails=reply_to,
                        subject=reply_subject,
                        body=reply_body,
                        cc_emails=cc_emails,
                        bcc_emails=bcc_emails,
                        attachment_paths=attachment_paths
                    )

                    return result
                else:
                    return {'success': False, 'error': "Failed to retrieve original message"}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def read_emails(self, mailbox: str = 'INBOX', search_criteria: str = 'UNSEEN',
                    max_emails: int = 10, mark_as_seen: bool = False) -> List[Dict[str, Any]]:
        """
        Read emails from a specified mailbox using IMAP.

        Args:
            mailbox: IMAP mailbox name (default: INBOX)
            search_criteria: IMAP search criteria (default: UNSEEN)
            max_emails: Maximum number of emails to fetch
            mark_as_seen: Whether to mark fetched emails as seen/read

        Returns:
            List of email data dictionaries
        """
        email_list = []

        try:
            # Connect to IMAP server
            with imaplib.IMAP4_SSL(self.imap_host, self.imap_port) as imap:
                imap.login(self.email_address, self.password)

                # Select mailbox
                status, messages = imap.select(
                    mailbox, readonly=(not mark_as_seen))
                if status != 'OK':
                    return []

                # Search for messages
                status, messages = imap.search(None, search_criteria)
                if status != 'OK':
                    return []

                # Get message IDs
                message_ids = messages[0].split()
                if not message_ids:
                    return []

                # Limit the number of emails to fetch
                message_ids = message_ids[-min(max_emails, len(message_ids)):]

                # Process each email
                for msg_id in reversed(message_ids):  # Get newest first
                    status, msg_data = imap.fetch(msg_id, '(RFC822)')
                    if status != 'OK':
                        continue

                    # Parse the email
                    msg = email.message_from_bytes(msg_data[0][1])

                    # Extract basic email information
                    email_data = {
                        'message_id': msg_id.decode(),
                        'smtp_message_id': msg.get('Message-ID', ''),
                        'subject': msg.get('Subject', ''),
                        'from': msg.get('From', ''),
                        'to': msg.get('To', ''),
                        'cc': msg.get('Cc', ''),
                        'date': msg.get('Date', ''),
                        'body': '',
                        'html_body': '',
                        'attachments': []
                    }

                    # Extract email from the "From" field using regex
                    email_match = re.search(r'<([^>]+)>', email_data['from'])
                    if email_match:
                        email_data['from_email'] = email_match.group(1)
                    else:
                        email_data['from_email'] = email_data['from']

                    # Extract body parts and attachments
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(
                            part.get('Content-Disposition'))

                        # Handle text parts
                        if content_type == 'text/plain' and 'attachment' not in content_disposition:
                            try:
                                payload = part.get_payload(decode=True)
                                if payload:
                                    email_data['body'] = payload.decode(
                                        'utf-8')
                            except:
                                pass

                        # Handle HTML parts
                        elif content_type == 'text/html' and 'attachment' not in content_disposition:
                            try:
                                payload = part.get_payload(decode=True)
                                if payload:
                                    email_data['html_body'] = payload.decode(
                                        'utf-8')
                            except:
                                pass

                        # Handle attachments
                        elif part.get_filename():
                            attachment = {
                                'filename': part.get_filename(),
                                'mimeType': content_type,
                                'size': len(part.get_payload(decode=True)) if part.get_payload(decode=True) else 0,
                                'content': part.get_payload(decode=True)
                            }
                            email_data['attachments'].append(attachment)

                    email_list.append(email_data)

            return email_list

        except Exception as e:
            print(f"Error reading emails: {str(e)}")
            return []

    def save_attachment(self, email_data: Dict[str, Any], attachment_index: int,
                        save_path: str) -> Dict[str, Any]:
        """
        Save an attachment from an email to a file.

        Args:
            email_data: Email data dictionary from read_emails
            attachment_index: Index of the attachment to save
            save_path: Directory path where to save the attachment

        Returns:
            Dict with status and saved file path
        """
        try:
            if not os.path.exists(save_path):
                os.makedirs(save_path)

            if attachment_index < 0 or attachment_index >= len(email_data['attachments']):
                return {'success': False, 'error': 'Invalid attachment index'}

            attachment = email_data['attachments'][attachment_index]
            filename = attachment['filename']
            file_path = os.path.join(save_path, filename)

            with open(file_path, 'wb') as f:
                f.write(attachment['content'])

            return {'success': True, 'file_path': file_path}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def filter_emails_by_conditions(self, emails: List[Dict[str, Any]],
                                    conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Filter emails based on specified conditions.

        Args:
            emails: List of email data dictionaries from read_emails
            conditions: Dictionary of conditions to filter by
                Supported keys:
                - subject_contains: List of strings to match in subject
                - from_contains: List of strings to match in from field
                - has_attachments: Boolean, True to require attachments
                - attachment_name_contains: List of strings to match in attachment names
                - body_contains: List of strings to match in email body

        Returns:
            Filtered list of email data dictionaries
        """
        filtered_emails = []

        for email_data in emails:
            match = True

            # Check subject condition
            if 'subject_contains' in conditions:
                subject_match = False
                for term in conditions['subject_contains']:
                    if term.lower() in email_data['subject'].lower():
                        subject_match = True
                        break
                if not subject_match:
                    match = False

            # Check from condition
            if match and 'from_contains' in conditions:
                from_match = False
                for term in conditions['from_contains']:
                    if term.lower() in email_data['from'].lower():
                        from_match = True
                        break
                if not from_match:
                    match = False

            # Check has_attachments condition
            if match and 'has_attachments' in conditions:
                if conditions['has_attachments'] and not email_data['attachments']:
                    match = False

            # Check attachment_name_contains condition
            if match and 'attachment_name_contains' in conditions:
                if email_data['attachments']:
                    attachment_match = False
                    for attachment in email_data['attachments']:
                        for term in conditions['attachment_name_contains']:
                            if term.lower() in attachment['filename'].lower():
                                attachment_match = True
                                break
                        if attachment_match:
                            break
                    if not attachment_match:
                        match = False
                else:
                    match = False

            # Check body_contains condition
            if match and 'body_contains' in conditions:
                body_match = False
                for term in conditions['body_contains']:
                    if term.lower() in email_data['body'].lower():
                        body_match = True
                        break
                if not body_match:
                    match = False

            if match:
                filtered_emails.append(email_data)

        return filtered_emails


def send_simple_email(email_address: str, app_password: str, recipient: str,
                      subject: str, body: str) -> Dict[str, Any]:
    """
    Send a simple email without attachments

    Args:
        email_address: Your Gmail address
        app_password: Your Gmail app password (not your regular password)
        recipient: Recipient email address
        subject: Email subject
        body: Email body text

    Returns:
        Dictionary with status information
    """
    # Initialize the client
    gmail_client = GmailSMTPClient(email_address, app_password)

    # Send the email
    result = gmail_client.send_email(
        to_emails=recipient,
        subject=subject,
        body=body
    )

    return result


def send_email_with_attachments(email_address: str, app_password: str,
                                recipient: str, subject: str, body: str,
                                attachment_paths: List[str]) -> Dict[str, Any]:
    """
    Send an email with file attachments

    Args:
        email_address: Your Gmail address
        app_password: Your Gmail app password (not your regular password)
        recipient: Recipient email address
        subject: Email subject
        body: Email body text
        attachment_paths: List of file paths to attach

    Returns:
        Dictionary with status information
    """
    # Initialize the client
    gmail_client = GmailSMTPClient(email_address, app_password)

    # Send the email with attachments
    result = gmail_client.send_email(
        to_emails=recipient,
        subject=subject,
        body=body,
        attachment_paths=attachment_paths
    )

    return result


def read_unread_emails(email_address: str, app_password: str, max_emails: int = 5) -> List[Dict[str, Any]]:
    """
    Read unread emails from inbox

    Args:
        email_address: Your Gmail address
        app_password: Your Gmail app password (not your regular password)
        max_emails: Maximum number of emails to retrieve

    Returns:
        List of dictionaries containing email data
    """
    # Initialize the client
    gmail_client = GmailSMTPClient(email_address, app_password)

    # Read unread emails
    emails = gmail_client.read_emails(
        search_criteria="UNSEEN",
        max_emails=max_emails
    )

    return emails


def find_emails_with_specific_attachments(email_address: str, app_password: str,
                                          attachment_keywords: List[str],
                                          max_emails: int = 20) -> List[Dict[str, Any]]:
    """
    Find emails containing attachments with specific keywords in filename

    Args:
        email_address: Your Gmail address
        app_password: Your Gmail app password (not your regular password)
        attachment_keywords: List of keywords to search for in attachment filenames
        max_emails: Maximum number of emails to retrieve

    Returns:
        Filtered list of emails containing matching attachments
    """
    # Initialize the client
    gmail_client = GmailSMTPClient(email_address, app_password)

    # Get recent emails with attachments
    emails = gmail_client.read_emails(
        search_criteria="UNSEEN",
        max_emails=max_emails
    )

    # Apply custom filtering
    conditions = {
        "has_attachments": True,
        "attachment_name_contains": attachment_keywords
    }

    filtered_emails = gmail_client.filter_emails_by_conditions(
        emails, conditions)
    return filtered_emails


def save_attachments_from_email(email_address: str, app_password: str,
                                search_terms: List[str], save_directory: str) -> Dict[str, Any]:
    """
    Find emails with specific subject terms and save their attachments

    Args:
        email_address: Your Gmail address
        app_password: Your Gmail app password (not your regular password)
        search_terms: List of terms to search for in email subjects
        save_directory: Directory to save attachments to

    Returns:
        Dict with status information and list of saved file paths
    """
    # Initialize the client
    gmail_client = GmailSMTPClient(email_address, app_password)

    # Get recent emails
    emails = gmail_client.read_emails(max_emails=20)

    # Filter emails by subject
    conditions = {
        "subject_contains": search_terms,
        "has_attachments": True
    }
    filtered_emails = gmail_client.filter_emails_by_conditions(
        emails, conditions)

    # Save all attachments from matching emails
    saved_files = []
    for email_data in filtered_emails:
        for idx, attachment in enumerate(email_data["attachments"]):
            result = gmail_client.save_attachment(
                email_data, idx, save_directory)
            if result["success"]:
                saved_files.append(result["file_path"])

    return {
        "success": True,
        "message": f"Saved {len(saved_files)} attachments",
        "saved_files": saved_files
    }


def reply_to_email_with_attachment(email_address: str, app_password: str,
                                   original_message_id: str, reply_body: str,
                                   attachment_paths: List[str] = None) -> Dict[str, Any]:
    """
    Reply to an email and include attachments

    Args:
        email_address: Your Gmail address
        app_password: Your Gmail app password (not your regular password)
        original_message_id: ID of the message to reply to
        reply_body: Body text for the reply
        attachment_paths: List of file paths to attach

    Returns:
        Dictionary with status information
    """
    # Initialize the client
    gmail_client = GmailSMTPClient(email_address, app_password)

    # Send reply with attachments
    result = gmail_client.reply_to_email(
        original_message_id=original_message_id,
        body=reply_body,
        include_original_content=True,
        attachment_paths=attachment_paths
    )

    return result


# Example usage
""" if __name__ == "__main__":
    # Replace with your Gmail credentials
    EMAIL = "your.email@gmail.com"
    # Use an App Password, not your regular password
    APP_PASSWORD = "your-app-password"

    # Example 1: Send a simple email
    result = send_simple_email(
        EMAIL,
        APP_PASSWORD,
        "recipient@example.com",
        "Test Email from SMTP Client",
        "This is a test email sent using the SMTP client."
    )
    print(f"Send simple email result: {result}")

    # Example 2: Send an email with attachments
    result = send_email_with_attachments(
        EMAIL,
        APP_PASSWORD,
        "recipient@example.com",
        "Test Email with Attachments",
        "Please find the requested documents attached.",
        ["path/to/document1.pdf", "path/to/document2.xlsx"]
    )
    print(f"Send email with attachments result: {result}")

    # Example 3: Read unread emails
    emails = read_unread_emails(EMAIL, APP_PASSWORD)
    print(f"Found {len(emails)} unread emails")

    # Example 4: Find emails with specific attachments
    filtered = find_emails_with_specific_attachments(
        EMAIL,
        APP_PASSWORD,
        ["invoice", "proposal", "contract"]
    )
    print(f"Found {len(filtered)} emails with matching attachments")

    # Example 5: Save attachments from specific emails
    save_result = save_attachments_from_email(
        EMAIL,
        APP_PASSWORD,
        ["proposal", "thầu"],
        "saved_attachments"
    )
    print(save_result["message"]) """
