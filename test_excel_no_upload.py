from app.config.env import EnvSettings
from app.mq.rabbit_mq import RabbitMQClient
from app.utils.exporter_v2 import process_excel_file_no_upload_with_compliance

# Lấy thông tin từ biến môi trường
env = EnvSettings()
rabbit_mq = RabbitMQClient(
    host=env.RABBIT_MQ_HOST,
    port=env.RABBIT_MQ_PORT,
    user=env.RABBIT_MQ_USER,
    password=env.RABBIT_MQ_PASS,
)

# Nhập giá trị từ người dùng
number = input("Nhập giá trị của a (mặc định là 3 nếu không nhập): ")
number = int(number) if number else 3

# Gửi message tương ứng vào queue
match number:
    case 1:
        next_queue = "extraction_queue"
        next_message = {
            "id": "6b36e92f-fd4f-57fc-9516-a819a79336d9",
            "files": [
                {
                    "mdpath": "markdown/20250404_014122_quangminhdinh38_gmail com_6 _Chuong_V _Yeu_cau_ve_ 1cad19da1c5780e4bb0cc52472e29d49.md",
                    "file_name": "quangminhdinh38_gmail com_6 _Chuong_V _Yeu_cau_ve_ 1cad19da1c5780e4bb0cc52472e29d49.md",
                    "bucket": "markdown",
                    "document_detail_id": 605,
                },
                {
                    "mdpath": "markdown/20250404_014156_20250404_012358_quangminhdinh38_gmail com_4 _Ho_so 1cad19da1c57800d9111c3d5ddd2b8ac.md",
                    "file_name": "20250404_012358_quangminhdinh38_gmail com_4 _Ho_so 1cad19da1c57800d9111c3d5ddd2b8ac.md",
                    "bucket": "markdown",
                    "document_detail_id": 606,
                },
                {
                    "mdpath": "markdown/20250404_014226_quangminhdinh38_gmail com_1 _T1hong_bao_moi_thau 1cad19da1c57804e9572e32f2edd7962.md",
                    "file_name": "quangminhdinh38_gmail com_1 _Thong_bao_moi_thau 1cad19da1c57804e9572e32f2edd7962.md",
                    "bucket": "markdown",
                    "document_detail_id": 607,
                }
            ]
        }
    case 2:
        next_queue = "sql_answer_queue"
        next_message = {
            "proposal_id": 682,
            "email_content_id": 529,
            "is_exist_contnet_markdown_hskt": True,
            "is_exist_contnet_markdown_tbmt": True,
            "is_exist_contnet_markdown_hsmt": True,
        }
    case 3:
        next_queue = "send_mail_queue"
        next_message = {
            'proposal_id': 682, 
            'email_content_id': 529, 
            'subject': 'Kết quả phân tích hồ sơ (30ccb7ff-0452-5efc-8a82-af161b7c555b)', 
            'body': 'Kính gửi anh chị,\nTrong file đính kèm là kết quả của hệ thống AI xử lý bóc tá', 
            'body': 'Kính gửi anh chị,\nTrong file đính kèm là kết quả của hệ thống AI xử lý bóc táh kèm là kết quả của hệ thống AI xử lý bóc tách yêu cầu tự động.\nVui lòng kiểm tra lại nội dung tài liệu này để đảm bảo tính chính xác của thông tin.', 
            'recipient': 'duyanhtutran@gmail.com', 
            'attachment_paths': 
                [
                    'C:/Users/TuTDA/AppData/Local/Temp/Checklist_HSMT_Trung_tam_thong_tin_tin_dung_Quoc_gia_Viet_Nam_Mua_ban_quyen_phan_mem_Microsoft_Office_LTSC_Standard_2021_va_dich_vu_trien_khai5e_clm3x.xlsx', 
                    'C:/gitlab/ai-proposal-mq/temp/TBDU_Kythuat_Trung_tam_thong_tin_tin_dung_Quoc_gia_Viet_Nam_Mua_ban_quyen_phan_mem_Microsoft_Office_LTSC_Standard_2021_va_dich_vu_trien_khai_2.docx', 
                    'C:/Users/TuTDA/Downloads/Tomtat_HSMT_Trung_tam_thong_tin_tin_dung_Quoc_gia_Viet_Nam_Mua_ban_quyen_phan_mem_Microsoft_Office_LTSC_Standard_2021_va_dich_vu_trien_khai_12.docx'
                ]
            }
    case 4:
        process_excel_file_no_upload_with_compliance(508, "Checklist_HSMT")

# Gửi message
rabbit_mq.publish(queue=next_queue, message=next_message)
