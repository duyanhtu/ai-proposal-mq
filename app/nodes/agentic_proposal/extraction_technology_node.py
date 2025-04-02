# Standard imports
import time

# Third party imports
from langchain_core.prompts import ChatPromptTemplate

# Your imports
from app.model_ai import llm
from app.nodes.states.state_proposal_v1 import StateProposalV1

import psycopg2
import json

def insert_technical_requirements(data):
    """
    Chèn dữ liệu vào bảng technical_requirement và technical_detail_requirement mà không dùng đệ quy
    """
    conn = psycopg2.connect(
        dbname="your_db",
        user="your_user",
        password="your_password",
        host="your_host",
        port="your_port"
    )
    cursor = conn.cursor()
    
    stack = [(None, data)]  # Dùng stack để xử lý dữ liệu thay vì đệ quy
    
    while stack:
        parent_id, requirements = stack.pop()
        
        for level in requirements:
            requirement_name = level.get("requirement_name", "")
            description = "\n".join([d["description_detail"] for d in level.get("description", [])]) if "description" in level else None
            
            cursor.execute(
                """
                INSERT INTO technical_requirement (proposal_id, requirements, description, id_original)
                VALUES (%s, %s, %s, %s) RETURNING id;
                """,
                (None, requirement_name, description, parent_id)
            )
            requirement_id = cursor.fetchone()[0]
            
            if "sub_requirements" in level:
                stack.append((requirement_id, level["sub_requirements"]))
    
    conn.commit()
    cursor.close()
    conn.close()



class ExtractionTechnologyMDNodeV1m0p0:
    """
    class ExtractionTechnologyMDNodeV1m0p0:

    Tương thích với phiên bản của tutda.
    Bóc tách thông tin các yêu cầu về yêu cầu kỹ thuật trong hồ sơ mời thầu .
    - Input: chapter_content: List[str]
    - Output: result_tecnology_experience: List[ExtractFinanceRequirement]
    """

    def __init__(self, name: str):
        self.name = name

    # Defining __call__ method
    def __call__(self, state: StateProposalV1):
        start_time = time.perf_counter()
        print(self.name)
        chapter_content = state["document_content_markdown_hskt"]
        # Không có chương liên quan để bóc tách
        if len(chapter_content) < 1:
            return {
                "result_extraction_experience": [],
            }
        # Có chương liên quan
        # Gọi model xử lý bóc tách dữ liệu về yêu cầu năng lực kinh nghiệm
        prompt_template = """
            Bạn là một chuyên gia trích xuất các yêu cầu của hồ sơ mời thầu.
            Hãy lấy các yêu cầu kỹ thuật theo quy tắc sau:
            1. Trích xuất toàn bộ dữ liệu có trong yêu cầu kỹ thuật bao gồm:
                Yêu cầu chung,
                Yêu cầu chức năng nghiệp vụ, 
                Yêu cầu kiến trúc, 
                Yêu cầu triển khai, 
                Yêu cầu bảo mật, 
                Yêu cầu đào tạo & bàn giao, 
                Yêu cầu bản quyền,
                Yêu cầu bảo hành bảo trì,
                Yêu cầu dịch vụ triển khai,
                Yêu cầu thông số kỹ thuật của thiết bị,
                Yêu cầu về tiến độ cung cấp hàng hóa, dịch vụ,
                Yêu cầu kỹ thuật đối với các thiết bị phần cứng (máy chủ quản trị sao lưu -Backup server),
                Yêu cầu phần mềm (Máy chủ tường lửa bảo vệ CSDL-DB firewall server, bản quyền phần mềm phục vụ quản trị, vận hành CSDL... )
                Các yêu cầu khác(nếu có)
            **CHÚ Ý:** Nếu không tìm thấy một trong các mục trên thì bỏ qua.
                    Không lấy các thông tin về giới thiệu chung về gói thầu.
                    KHông lấy thông tin phạm vi gói thầu
            2. Nếu yêu cầu nằm trong table :
                - Mô tả yêu cầu được viết trong 1 đoạn (ngăn cách bằng |   |) với 
                - Nội dung cần trích xuất bắt đầu từ dấu `|` và kết thúc ngay trước dấu `|` tiếp theo (hoặc hết nội dung nếu không có dấu `|` tiếp theo).
                - Giữ nguyên toàn bộ nội dung gốc trong khoảng giữa hai dấu `|`, bao gồm cả định dạng văn bản, ký tự xuống dòng, hoặc ký tự đặc biệt nếu có, xóa dấu `|`.
                - Nếu không tìm thấy cặp dấu `|` nào, trả về mảng rỗng.
                - Trong nội dung có các chú ý trong dấu () thì hãy lấy hết nội dung trong ngoặc đó như Điều khoản (3), Nghị định (8), Tiết (e), v.v. 
                - Nếu dạng table thì mỗi row cho vào 1 description_detail riêng biệt.
           
            3. Trích xuất toàn bộ dữ liệu của hàng để lấy tên yêu cầu, mô tả của yêu cầu .
            4. Trong yêu cầu nếu có lưu ý trong ngoặc() hãy trích xuất đầy đủ thông tin trong ngoặc.
            5. Bỏ qua các chỉ mục ví dụ 3.1, 3.2,.... và lấy đúng tên yêu cầu cần lấy.
            6. Ví dụ chỉ để tham khảo KHÔNG phải là nội dung cần bóc tách.
            8. Đầu ra hãy trả về dạng mảng các JSON.
 
            **Ví dụ**
[
    "requirement_level_0": {{
        "muc": "3",
        "requirement_name": "Yêu cầu về kỹ thuật chi tiết",
        "sub_requirements": [
            {{
                "requirement_level_1": {{
                    "muc": "3.3",
                    "requirement_name": "Yêu cầu nội dung công việc bảo trì",
                    "sub_requirements": [
                        {{
                            "requirement_level_2": {{
                                "muc": "3.3.1",
                                "requirement_name": "Yêu cầu chung",
                                "description": [
                                    {{
                                        "description_detail": "Kiểm tra, bảo trì định kỳ: Trong thời gian bảo trì, định kỳ tối thiểu 03 tháng/01 lần (hoặc ngay khi có yêu cầu của Agribank) thực hiện kiểm tra, bảo dưỡng định kỳ cho các thiết bị thuộc phạm vi bảo trì, rà soát cấu hình, đánh giá hiệu năng sử dụng, đưa ra các khuyến nghị để tối ưu thiết bị (nếu có)."
                                    }},
                                    {{
                                        "description_detail": "Hỗ trợ kỹ thuật và xử lý, khắc phục sự cố: Trong thời gian bảo trì, đơn vị cung cấp dịch vụ bảo trì phải cung cấp dịch vụ hỗ trợ kỹ thuật và khắc phục sự cố thiết bị. Khi có yêu cầu hỗ trợ kỹ thuật của Agribank hoặc khi thiết bị có sự cố, đơn vị cung cấp dịch vụ bảo trì có trách nhiệm hỗ trợ kỹ thuật và xử lý, khắc phục sự cố; trường hợp cần thiết đơn vị cung cấp dịch vụ bảo trì phải cử cán bộ trực tiếp tới địa điểm lắp đặt thiết bị hoặc yêu cầu hỗ trợ trợ kỹ thuật của hãng sản xuất để xử lý và khắc phục sự cố trong thời gian sớm nhất."
                                    }},
                                    {{
                                        "description_detail": "Cập nhật phần mềm hệ điều hành và phần mềm an ninh phòng chống tấn công xâm nhập (IPS) của thiết bị: Trong thời gian bảo trì, các thiết bị phải được thường xuyên, liên tục cập nhập phần mềm hệ điều hành thiết bị, bản vá lỗi, phần mềm an ninh phòng chống tấn công xâm nhập và các mẫu tấn công xâm nhập mới theo tiêu chuẩn của hãng sản xuất. Căn cứ các khuyến nghị/khuyến cáo của hãng sản xuất, yêu cầu của Agribank, đơn vị cung cấp phải chủ động tiến hành phân tích, lên kế hoạch để nâng cấp, cập nhật kịp thời nhằm giúp các thiết bị tường lửa hoạt động an toàn, ổn định, ngăn ngừa các lỗi và sự cố ảnh hưởng đến hoạt động hệ thống mạng."
                                    }}
                                ]
                            }}
                        }},
                        {{
                            "requirement_level_2": {{
                                "muc": "3.3.2",
                                "requirement_name": "Yêu cầu về công việc kiểm tra, bảo trì định kỳ",
                                "sub_requirements": [
                                    {{
                                        "requirement_level_3": {{
                                            "muc": "a",
                                            "requirement_name": "Kiểm tra, vệ sinh thiết bị",
                                            "description": [
                                                {{
                                                    "description_detail": "Kiểm tra môi trường hoạt động của thiết bị, nguồn điện, nhiệt độ."
                                                }},
                                                {{
                                                    "description_detail": "Kiểm tra dây cáp, đầu kết nối mạng. Sắp xếp gọn gàng và cố định các dây cáp kết nối mạng trên thiết bị."
                                                }},
                                                {{
                                                    "description_detail": "Thực hiện bảo dưỡng, vệ sinh thiết bị, nguồn, cổng kết nối, module SFP."
                                                }}
                                            ]
                                        }}
                                    }},
                                    {{
                                        "requirement_level_3": {{
                                            "muc": "b",
                                            "requirement_name": "Kiểm tra hoạt động, cấu hình và chính sách an ninh của thiết bị",
                                            "description": [
                                                {{
                                                    "description_detail": "Kiểm tra hiệu năng hoạt động của thiết bị: khả năng đáp ứng tài nguyên của bộ vi xử lý (CPU) và bộ nhớ (RAM)."
                                                }}
                                            ]
                                        }}
                                    }},
                                    {{
                                        "requirement_level_3": {{
                                            "muc": "c",
                                            "requirement_name": "Tối ưu cấu hình và chính sách an ninh mạng trên thiết bị",
                                            "description": [
                                                {{
                                                    "description_detail": "Rà soát các cấu hình và chính sách an ninh mạng được thiết lập trên thiết bị."
                                                }}
                                            ]
                                        }}
                                    }}
                                ]
                            }}
                        }}
                    ]
                }}
            }}
        ]
    }}
]

ví dụ khác:
{{
  "response": {{
    "requirement_level_0": {{
      "muc": "1.2",
      "requirement_name": "Yêu cầu về kỹ thuật chi tiết",
      "sub_requirements": [
        {{
          "requirement_level_1": {{
            "muc": "1.2.1",
            "requirement_name": "Yêu cầu kỹ thuật đối với các thiết bị, phần mềm thương mại tại TTDL chính",
            "sub_requirements": [
              {{
                "requirement_level_2": {{
                  "muc": "1",
                  "requirement_name": "Hệ thống máy chủ chuyên dụng thực thi CSDL",
                  "sub_requirements": [
                    {{
                      "requirement_level_3": {{
                        "requirement_name": "Thiết bị máy chủ, lưu trữ và chuyển mạch",
                        "description": [
                          {{
                            "description_detail": "Máy chủ CSDL | Processor: 32 cores hoặc tương đương\nMemory: 1024 GB\nStorage: 02*3,84TB NVMe SSD\nExternal connectivity: 04*(25 Gbps optical ethernet port with transceiver/adapter)\nInternal connectivity: 2* 100 Gbps port with adapter/transceiver\nOperating system: Oracle Linux hoặc tương đương với quyền sử dụng đầy đủ cho tất cả các lõi vi xử lý – cores của server\nVirtualization software: Oracle KVM hoặc tương đương với quyền sử dụng đầy đủ cho tất cả các lõi vi xử lý – cores của server\nRedundant hot-swappable power supplies & fans\nLinh phụ kiện:\n+ ≥ 4 transceiver 25GE (tương thích với thiết bị chuyển mạch leaf Cisco C9300 series) để kết nối vào hệ thống mạng\n+ ≥ 4 dây nhảy quang ≥15m tương thích 10/25GE + Linh phụ kiện khác"
                          }},
                          {{
                            "description_detail": "Máy chủ lưu trữ | Processor: 16 cores enable\nMemory: 256 GB\nStorage: 6x18 TB HDD\nFlash Capacity (raw): 2x 6.4TB"
                          }}
                        ]
                      }}
                    }}
                  ]
                }}
              }},
              {{
                "requirement_level_2": {{
                  "muc": "2",
                  "requirement_name": "Máy chủ tường lửa bảo vệ CSDL - DB Firewall servers",
                  "sub_requirements": [
                    {{
                      "requirement_level_3": {{
                        "requirement_name": "Thiết bị máy chủ tường lửa bảo vệ CSDL - DB Firewall servers",
                        "description": [
                          {{
                            "description_detail": "2x CPU 18-cores\n8x 32 GB DDR4-3200 registered DIMM\n2x One 3.84 TB 2.5-inch NVMe PCIe 4.0\n1x Dual Port 16 Gb or 32 Gb Fibre Channel PCIe HBA with 2 transceivers, Qlogic 1x Dual Port 25 Gb Ethernet Adapter kèm transceiver 25G\n2x nguồn dự phòng\nLinh phụ kiện..."
                          }}
                        ]
                      }}
                    }}
                  ]
                }}
              }},
              {{
                "requirement_level_2": {{
                  "muc": "3",
                  "requirement_name": "Máy chủ quản trị sao lưu - Backup Server",
                  "sub_requirements": [
                    {{
                      "requirement_level_3": {{
                        "requirement_name": "Thiết bị máy chủ quản trị sao lưu -Backup server",
                        "description": [
                          {{
                            "description_detail": "2x CPU 16-core 2.4 GHz processor\n8x 32 GB DDR4-3200 registered DIMM\n2x One 3.84 TB 2.5-inch NVMe PCIe 4.0\n1x Dual Port 16 Gb or 32 Gb..."
                          }},
                         ]
                      }}
                    }}
                  ]
                }}
              }},
			  {{
                "requirement_level_2": {{
                  "muc": "4",
                  "requirement_name": "Bản quyền Phần mềm phục vụ quản trị , vận hành CSDL ",
                  "sub_requirements": [
                    {{
                      "requirement_level_3": {{
                        "requirement_name": "Phần mềm quản trị cơ sở dữ liệu bao gồm 1 năm bảo hành và hỗ trợ kỹ thuật của nhà sản xuất ",
                        "description": [
                          {{
                            "description_detail": "-	Hệ quản trị CSDL có thể hoạt động trên nhiều nền tảng phần cứng, nền tảng hệ điều hành khác nhau..."
                          }},
                         ]
                      }}
                    }}
                  ]
                }}
              }}
            ]
          }}
        }}
      ]
    }}
  }}
}}

Return only the JSON in this format:
           
[
    {{
        "requirement_level_0": {{
            "muc": "tên chỉ mục",
            "requirement_name": "Yêu cầu về kỹ thuật chi tiết",
            "sub_requirements": [
                {{
                    "requirement_level_1": {{
                        "muc": "tên chỉ mục",
                        "requirement_name": "tên yêu cầu là các yêu cầu trong phạm vi mô tả ở trên có level nhỏ hơn level 0",
                        "sub_requirements": [
                            {{
                                "requirement_level_2": {{
                                     "muc": "tên chỉ mục",
                                    "requirement_name": "tên yêu cầu là các yêu cầu có level nhỏ hơn level 1",
                                    "sub_requirements": [
                                        {{
                                            "requirement_level_3": {{
                                                "requirement_name": "tên yêu cầu là các yêu cầu có level nhỏ hơn level 2",
                                                "description": [
                                                    {{
                                                        "description_detail": "mô tả từng chi tiết của yêu cầu, nếu không có yêu cầu bắt buộc để giá trị NA"
                                                    }}
                                                ]
                                            }}
                                        }}
                                    ]
                                }}
                            }}
                        ]
                    }}
                }}
            ]
        }}
    }}
]          
                                       
               
            Nội dung hồ sơ mời thầu:
            {content}
        """

        chat_prompt_template = ChatPromptTemplate.from_template(prompt_template)

        prompt = chat_prompt_template.invoke({"content": chapter_content})

        response = (
            llm.chat_model_gpt_4o_mini_16k()
            .with_structured_output(None, method="json_mode")
            .invoke(prompt)
        )
        print("TECHNOLOGY: ",response)
        finish_time = time.perf_counter()
        print(f"Total time: {finish_time - start_time} s")
        return {"result_extraction_technology": response}