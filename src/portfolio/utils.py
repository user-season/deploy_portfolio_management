from decimal import Decimal
import requests



def generate_qr_code(amount, transaction_id, username=None):
    """
    Tạo QR code VietQR cho giao dịch chuyển khoản ngân hàng
    
    Args:
        amount (float): Số tiền cần chuyển khoản
        transaction_id (str): Mã giao dịch để ghi trong nội dung chuyển khoản
        username (str, optional): Tên người dùng để thêm vào nội dung chuyển khoản
        
    Returns:
        str: URL của hình ảnh QR code
    """
    # Thông tin ngân hàng mặc định (MB Bank)
    BANK_ID = "MB"
    ACCOUNT_NO = "0967720844"
    
    # Tạo nội dung chuyển khoản bao gồm mã giao dịch, số tiền và tên người dùng
    transfer_content = transaction_id
    if amount:
        transfer_content += f" {amount}"
    if username:
        transfer_content += f" {username}"
    
    # Tạo URL QR code từ VietQR
    qr_url = f"https://img.vietqr.io/image/{BANK_ID}-{ACCOUNT_NO}-compact2.png?amount={amount}&addInfo={transfer_content}"
    
    return qr_url

def check_paid(transaction_id=None, amount=None):
    """
    Kiểm tra thông tin giao dịch nạp tiền từ API
    
    Args:
        transaction_id (str, optional): Mã giao dịch cần kiểm tra
        amount (Decimal, optional): Số tiền cần kiểm tra
        
    Returns:
        dict: Kết quả kiểm tra với các thông tin:
            - success (bool): Thành công hay không
            - message (str): Thông báo kết quả
            - data (dict): Dữ liệu giao dịch nếu tìm thấy
            - match_transaction (bool): Có trùng mã giao dịch không
            - match_amount (bool): Có trùng số tiền không
    """
    result = {
        'success': False,
        'message': '',
        'data': None,
        'match_transaction': False,
        'match_amount': False
    }
    
    try:
        print(f"[DEBUG] Đang kiểm tra giao dịch với mã: {transaction_id}, số tiền: {amount}")
        
        # URL API lấy thông tin giao dịch
        url = "https://script.googleusercontent.com/macros/echo?user_content_key=AehSKLgCoMh1JB6pFLJafVjP7sVQi3PJxLfpVv_gyUFSucJPE2sl_ZFuxRCClfN_6HVUDuv4PlZ6OXlJKoFc76l6NjufxugonvGFjvIL0i2nAzYDofg-zL_AJihhpNqHSeBrDPziFobF-Z1K-gAX51FSqggd8R5rs522K3apY-LIjQb373HY_iY7HFAU2X8l8416q46_Uk9VhUEq5I4PUEYAv9CPfe132xC0px8C_-IIQ6ETormkarUr_cfY9xRLu1atd9uiToF0rcsDx55VMAKA7mof4zAFfg&lib=MCHFsWSHu2AnRDw8q22GOYXaf-U4XPmlc"
        print(f"[DEBUG] Đang truy vấn API với transaction_id: {transaction_id}")
        
        response = requests.get(url)
        response.raise_for_status()  # Nếu lỗi HTTP thì raise exception
        data = response.json()
        transactions = data["data"]
        
        # In thông tin debug
        print(f"[DEBUG] Đã nhận được {len(transactions)} giao dịch từ API")
        for idx, trans in enumerate(transactions):
            desc = trans.get("Mô tả", "")
            code = desc.split()[0] if desc else ""
            print(f"[DEBUG] Giao dịch #{idx+1}: Mã={code}, Mô tả={desc}, Giá trị={trans.get('Giá trị', 'N/A')}")
        
        # Nếu không cung cấp mã giao dịch, trả về giao dịch mới nhất
        if not transaction_id:
            last_transaction = transactions[-1]
            result['data'] = last_transaction
            result['success'] = True
            result['message'] = "Lấy thông tin giao dịch mới nhất thành công"
            return result
        
        # Kiểm tra từng giao dịch để tìm mã giao dịch trùng khớp
        found_transaction = None
        
        for transaction in transactions:
            # Lấy mô tả giao dịch
            description = transaction.get("Mô tả", "")
            
            # Lấy từ đầu tiên trong mô tả (mã giao dịch)
            transaction_code = description.split()[0] if description else ""
            
            # In thông tin debug cho mỗi giao dịch được kiểm tra
            print(f"[DEBUG] Đang so sánh: {transaction_code} với {transaction_id}")
            
            # Kiểm tra nếu mã giao dịch trùng khớp
            if transaction_code == transaction_id:
                found_transaction = transaction
                transaction_amount = Decimal(str(transaction.get("Giá trị", 0)))
                
                result['data'] = found_transaction
                result['match_transaction'] = True
                
                # Kiểm tra số tiền nếu được cung cấp
                if amount is not None:
                    if not isinstance(amount, Decimal):
                        amount = Decimal(str(amount))
                    result['match_amount'] = abs(transaction_amount - amount) < Decimal('1000')  # Cho phép sai số nhỏ
                    
                    if result['match_amount']:
                        result['success'] = True
                        result['message'] = f"Xác nhận nạp tiền thành công với mã giao dịch {transaction_id}, số tiền {transaction_amount:,.0f} VNĐ"
                    else:
                        result['success'] = False
                        result['message'] = f"Mã giao dịch {transaction_id} hợp lệ nhưng số tiền không đúng. Số tiền chuyển: {transaction_amount:,.0f} VNĐ, Số tiền cần nạp: {amount:,.0f} VNĐ"
                else:
                    result['success'] = True
                    result['message'] = f"Tìm thấy giao dịch với mã {transaction_id}"
                
                return result
        
        # Không tìm thấy giao dịch
        if not found_transaction:
            result['success'] = False
            result['message'] = f"Không tìm thấy giao dịch với mã {transaction_id}"
            print(f"[DEBUG] Không tìm thấy giao dịch nào khớp với mã: {transaction_id}")
            
            # Thử tìm giao dịch với nội dung chứa mã giao dịch (trường hợp không phải từ đầu tiên)
            possible_match = None
            for transaction in transactions:
                description = transaction.get("Mô tả", "")
                if transaction_id in description:
                    possible_match = transaction
                    print(f"[DEBUG] Tìm thấy giao dịch có chứa mã: {transaction_id} trong mô tả: {description}")
                    break
                    
            if possible_match:
                result['message'] += f". Tuy nhiên, có một giao dịch chứa mã này trong nội dung: {possible_match.get('Mô tả', '')}"
            
            # Kiểm tra giao dịch mới nhất
            if transactions:
                latest = transactions[-1]
                latest_desc = latest.get("Mô tả", "")
                latest_code = latest_desc.split()[0] if latest_desc else ""
                result['message'] += f". Giao dịch mới nhất có mã: {latest_code}"
            
    except Exception as e:
        result['success'] = False
        result['message'] = f"Lỗi khi kiểm tra giao dịch: {str(e)}"
        print(f"[DEBUG] Exception: {str(e)}")
    
    return result 