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
number = input("Nhập giá trị của a: ")
number = int(number) if number else 3

# Gửi message tương ứng vào queue
match number:
    case 1:
        next_queue = "extraction_queue_dev_tutda"
        next_message = {
            "id": "1c5b8292-5917-54d6-b3ee-5ff880e87121",
            "files": [
                {
                    "mdpath": "markdown/20250513_172032_20250513_101909_20251305101906_hattl_hpt vn_ho_so_ 1f268e74b4268036bc00fbb7f8039915.md",
                    "file_name": "20250513_101909_20251305101906_hattl_hpt vn_ho_so_ 1f268e74b4268036bc00fbb7f8039915.md",
                    "bucket": "markdown",
                    "document_detail_id": 453,
                    "link_md": "markdown/20250513_172032_20250513_101909_20251305101906_hattl_hpt vn_ho_so_ 1f268e74b4268036bc00fbb7f8039915.md",
                    "file_name_md": "20250513_101909_20251305101906_hattl_hpt vn_ho_so_ 1f268e74b4268036bc00fbb7f8039915.md",
                    "classify_type": "TEXT",
                },
                {
                    "mdpath": "ai-proposal/20251305101906_hattl_hpt.vn_02_chuong_v_yeu_cau_ky_thuat_csbm_firewall.update.docx",
                    "file_name": "20250513_101906_02 Chuong V_YÃªu cáº§u ká»¹ thuáº­t CSBM Firewall.update_7d979f95.md",
                    "bucket": "markdown",
                    "document_detail_id": 452,
                    "link_md": "markdown/20250513_101906_02 Chuong V_YÃªu cáº§u ká»¹ thuáº­t CSBM Firewall.update_7d979f95.md",
                    "file_name_md": "20250513_101906_02 Chuong V_YÃªu cáº§u ká»¹ thuáº­t CSBM Firewall.update_7d979f95.md",
                    "classify_type": "DOCX",
                },
            ],
        }
    case 2:
        next_queue = "sql_answer_queue_dev_tutda"
        # next_message = {
        #     "hs_id": "dfbadd71-b86e-5e28-81c5-41a541ec1eb6",
        #     "proposal_id": 166,
        #     "email_content_id": 457,
        #     "is_exist_contnet_markdown_hskt": True,
        #     "is_exist_contnet_markdown_tbmt": True,
        #     "is_exist_contnet_markdown_hsmt": True,
        # }
        next_message = {
            "hs_id": "b601a185-9328-51ac-bbf7-5551136062ab",
            "proposal_id": 64,
            "email_content_id": 248,
            "is_data_extracted_finance": False,
            "is_exist_contnet_markdown_hskt": False,
            "is_exist_contnet_markdown_tbmt": False,
            "is_exist_contnet_markdown_hsmt": True,
        }
    case 3:
        next_queue = "send_mail_queue_dev_tutda"
        next_message = {
            "proposal_id": 896,
            "email_content_id": 1235,
            "subject": "Kết quả phân tích hồ sơ (39d772a9-001f-569c-ad6d-077eba493ece)",
            "body": "Kính gửi anh chị,\nTrong file đính kèm là kết quả của hệ thống AI xử lý bóc tá",
            "body": "Kính gửi anh chị,\nTrong file đính kèm là kết quả của hệ thống AI xử lý bóc táh kèm là kết quả của hệ thống AI xử lý bóc tách yêu cầu tự động.\nVui lòng kiểm tra lại nội dung tài liệu này để đảm bảo tính chính xác của thông tin.",
            "recipient": "duyanhtutran@gmail.com",
            "attachment_paths": [
                "/tmp/Checklist_HSMT_NGAN_HANG_THUONG_MAI_CO_PHAN_NGOAI_THUONG_VIET_NAM_au_tu_he_thong_kiem_soat_du_lieu_qua_cac_kenh_trao_oi_file_dua_tren_cong_nghe_CDRv7u6br_f.xlsx",
                "",
                "/root/Downloads/Tomtat_HSMT_NGAN_HANG_THUONG_MAI_CO_PHAN_NGOAI_THUONG_VIET_NAM_au_tu_he_thong_kiem_soat_du_lieu_qua_cac_kenh_trao_oi_file_dua_tren_cong_nghe_CDR.docx",
            ],
        }
    case 4:
        process_excel_file_no_upload_with_compliance(508, "Checklist_HSMT")
    case 5:
        import json

        # Dữ liệu đầu vào là một mảng requirement_level_0
        data = json.loads({})

        # Tạo bản mới để gom dữ liệu
        merged = {
            "requirement_level_0": {
                "muc": "1.",
                "requirement_name": "Yêu cầu về kỹ thuật",
                "sub_requirements": [],
            }
        }

        # Duyệt qua từng phần tử để gộp sub_requirements
        for item in data:
            sub_reqs = item["requirement_level_0"].get("sub_requirements", [])
            merged["requirement_level_0"]["sub_requirements"].extend(sub_reqs)

        # Kết quả là một object duy nhất
        result = json.dumps(merged, indent=2, ensure_ascii=False)
        print(result)
        # Gửi message
    case 6:
        next_queue = "send_mail_queue_dev_tutda"
        next_message = {
            "hs_id": "e45fbf52-6597-5a5e-b97c-58aa7140d402",
            "proposal_id": "",
            "subject": "Kết quả phân tích hồ sơ (350)",
            "body": "Kính gửi anh chị,\nHiện tại hệ thống không thể xử lý hồ sơ mời thầu này.",
            "recipient": "duyanhtutran@gmail.com",
            "attachment_paths": [],
        }
    case 7:
        next_queue = "chapter_splitter_queue_dev_tutda"
        next_message = {
            "hs_id": "e45fbf52-6597-5a5e-b97c-58aa7140d402",
            "proposal_id": "",
            "subject": "Kết quả phân tích hồ sơ (350)",
            "body": "Kính gửi anh chị,\nHiện tại hệ thống không thể xử lý hồ sơ mời thầu này.",
            "recipient": "duyanhtutran@gmail.com",
            "attachment_paths": [],
        }

rabbit_mq.publish(queue=next_queue, message=next_message)
