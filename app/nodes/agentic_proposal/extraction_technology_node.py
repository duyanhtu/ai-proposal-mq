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
                "result_extraction_technology": [],
            }
        # Có chương liên quan
        # Gọi model xử lý bóc tách dữ liệu về yêu cầu năng lực kinh nghiệm
        prompt_template = """                           
            Bạn là một chuyên gia trích xuất các yêu cầu của hồ sơ mời thầu.
            Hãy lấy các yêu cầu kỹ thuật theo quy tắc sau:
            1. Trích xuất dữ liệu nếu có trong hồ sơ mời thầu về các yêu cầu sau :
                Yêu cầu chung,
                Yêu cầu chức năng nghiệp vụ, 
                Yêu cầu kiến trúc, 
                Yêu cầu triển khai, 
                Yêu cầu bảo mật, 
                Yêu cầu đào tạo & bàn giao, 
                Yêu cầu bản quyền, bảo hành bảo trì,
                Yêu cầu dịch vụ triển khai,
                Yêu cầu thông số kỹ thuật của thiết bị,
                Yêu cầu về tiến độ cung cấp hàng hóa, dịch vụ,       
                yêu cầu chức năng nghiệp vụ, 
                yêu cầu sizing, 
                yêu cầu license ,
                yêu cầu thời gian,
                yêu cầu khác
            **CHÚ Ý:** PHẢI lấy đầy đủ nội dung yêu cầu và mô tả chi tiết yêu cầu trong tài liệu theo dữ liệu gốc.
                    Nếu không tìm thấy một trong các mục trên thì bỏ qua.
                    Không lấy các thông tin về giới thiệu chung về gói thầu.
                    KHông lấy thông tin phạm vi gói thầu
                    KHÔNG lấy tiêu đề cột trong bảng làm yêu cầu.
                    KHÔNG tách nội dung mô tả để làm yêu cầu
                    Các yêu cầu phải theo heading hoặc các yêu cầu được mô tả trong bảng.
            2. Mô tả yêu cầu được viết trong 1 đoạn (ngăn cách bằng |   |) với 
                - Nội dung cần trích xuất bắt đầu từ dấu `|` và kết thúc ngay trước dấu `|` tiếp theo (hoặc hết nội dung nếu không có dấu `|` tiếp theo).
                - Giữ nguyên toàn bộ nội dung gốc trong khoảng giữa hai dấu `|`, bao gồm cả định dạng văn bản, ký tự xuống dòng, hoặc ký tự đặc biệt nếu có, xóa dấu `|`.
                - Nếu không tìm thấy cặp dấu `|` nào, trả về mảng rỗng.
                - Trong nội dung có các chú ý trong dấu () thì hãy lấy hết nội dung trong ngoặc đó như Điều khoản (3), Nghị định (8), Tiết (e), v.v. 
                - Nếu dạng table thì mỗi row cho vào 1 description_detail riêng biệt.
                - KHông lấy tiêu đề cột trong bảng để làm yêu cầu.(ví dụ Thông số kỹ thuật/Yêu cầu dịch vụ  là tên cột của bảng yêu cầu cần bóc tách thì không đưa thành yêu cầu)
            3. Trích xuất toàn bộ dữ liệu của hàng để lấy tên yêu cầu, mô tả của yêu cầu và nối thêm thang điểm chi tiết nếu có, mẫu số tài liệu.
            4. Trong yêu cầu nếu có lưu ý trong ngoặc() hãy trích xuất đầy đủ thông tin trong ngoặc.
            5. Bỏ qua các chỉ mục ví dụ 3.1, 3.2,.... và lấy đúng tên yêu cầu cần lấy.
            6. Ví dụ chỉ để tham khảo KHÔNG phải là nội dung cần bóc tách.
            7. Đầu ra hãy trả về dạng JSON.
 
            **Ví dụ**
    Ví dụ 1: có input như sau:
    **3.3Yêu cầu nội dung công việc bảo trì**
      3.3.1 Yêu cầu chung

        -Kiểm tra, bảo trì định kỳ: Trong thời gian bảo trì, định kỳ tối thiểu 03 tháng/01 lần (hoặc ngay khi có yêu cầu của Agribank) thực hiện kiểm tra, bảo dưỡng định kỳ cho các thiết bị thuộc phạm vi bảo trì, rà soát cấu hình, đánh giá hiệu năng sử dụng, đưa ra các khuyến nghị để tối ưu thiết bị (nếu có).

        - Hỗ trợ kỹ thuật và xử lý, khắc phục sự cố: Trong thời gian bảo trì, đơn vị cung cấp dịch vụ bảo trì phải cung cấp dịch vụ hỗ trợ kỹ thuật và khắc phục sự cố thiết bị. Khi có yêu cầu hỗ trợ kỹ thuật của Agribank hoặc khi thiết bị có sự cố, đơn vị cung cấp dịch vụ bảo trì có trách nhiệm hỗ trợ kỹ thuật và xử lý, khắc phục sự cố; trường hợp cần thiết đơn vị cung cấp dịch vụ bảo trì phải cử cán bộ trực tiếp tới địa điểm lắp đặt thiết bị hoặc yêu cầu hỗ trợ trợ kỹ thuật của hãng sản xuất để xử lý và khắc phục sự cố trong thời gian sớm nhất.
        - Cập nhật phần mềm hệ điều hành và phần mềm an ninh phòng chống tấn công xâm nhập (IPS) của thiết bị: Trong thời gian bảo trì, các thiết bị phải được thường xuyên, liên tục cập nhập phần mềm hệ điều hành thiết bị, bản vá lỗi, phần mềm an ninh phòng chống tấn công xâm nhập và các mẫu tấn công xâm nhập mới theo tiêu chuẩn của hãng sản xuất. Căn cứ các khuyến nghị/khuyến cáo của hãng sản

        3

        xuất, yêu cầu của Agribank, đơn vị cung cấp phải chủ động tiến hành phân tích, lên kế hoạch để nâng cấp, cập nhật kịp thời nhằm giúp các thiết bị tường lửa hoạt động an toàn, ổn định, ngăn ngừa các lỗi và sự cố ảnh hưởng đến hoạt động hệ thống mạng.
Output mong muốn như sau:
[
    "requirement_level_0": {{
        "muc": "3",
        "requirement_name": "Yêu cầu về kỹ thuật",
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
ví dụ 2: 
OUTPUT NHƯ SAU:
{{
	"requirement_level_0": {{
		"muc": "1.",
		"requirement_name": "Yêu cầu về kỹ thuật",
		"sub_requirements": [
			{{
				"requirement_level_1": {{
					"muc": "1.2.",
					"requirement_name": "Yêu cầu về kỹ thuật",
					"sub_requirements": [
						{{
							"requirement_level_2": {{
								"muc": "1",
								"requirement_name": "Bản quyền phần mềm Microsoft Office LTSC Standard 2021",
								"description": [
									{{
										"description_detail": "Đảm bảo tương thích với hệ điều hành Windows 10, Windows 11"
									}},
									{{
										"description_detail": "Bao gồm các ứng dụng cơ bản như Word, Excel, PowerPoint và Outlook."
									}}
								]
							}}
						}}
					]
				}},
				"requirement_level_1": {{
					"muc": "1.3.",
					"requirement_name": "Các yêu cầu khác",
					"sub_requirements": [
						{{
							"requirement_level_2": {{
								"muc": "1.3.1",
								"requirement_name": "Yêu cầu về Bản quyền",
								"description": [
									{{
										"description_detail": "- Hàng hóa cung cấp mới 100% chưa qua sử dụng"
									}},
									{{
										"description_detail": "- Có Giấy phép hoặc giấy ủy quyền bán hàng của nhà sản xuất, đại lý phân phối hoặc giấy chứng nhận quan hệ đối tác hoặc tài liệu khác có giá trị tương đương."
									}}
								]
							}}
						}},
						{{
							"requirement_level_2": {{
								"muc": "1.3.2",
								"requirement_name": "Yêu cầu về bảo hành, hỗ trợ kỹ thuật",
								"description": [
									{{
										"description_detail": "Nhà thầu phải có văn phòng hoặc cơ sở tại Hà Nội "
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

Return only the JSON in this format:
           
[
    {{
        "requirement_level_0": {{
            "muc": "số chỉ mục",
            "requirement_name": "Yêu cầu kỹ thuật",
            "sub_requirements": [
                {{
                    "requirement_level_1": {{
                        "muc": "số chỉ mục",
                        "requirement_name": "tên yêu cầu là các yêu cầu trong phạm vi mô tả ở trên có level nhỏ hơn level 0",
                        "sub_requirements": [
                            {{
                                "requirement_level_2": {{
                                     "muc": "số chỉ mục",
                                    "requirement_name": "tên yêu cầu là các yêu cầu có level nhỏ hơn level 1",
                                    "sub_requirements": [
                                        {{
                                            "requirement_level_3": {{
                                                "requirement_name": "tên yêu cầu là các yêu cầu có level nhỏ hơn level 2",
                                                "description": [
                                                    {{
                                                        "description_detail": "mô tả từng chi tiết của yêu cầu"
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
        if "response" in response and isinstance(response["response"], list):
          data = response["response"]
        else: 
          data = response
        print("TECHNOLOGY: ",data)
        finish_time = time.perf_counter()
        print(f"Total time: {finish_time - start_time} s")
        return {"result_extraction_technology": data}