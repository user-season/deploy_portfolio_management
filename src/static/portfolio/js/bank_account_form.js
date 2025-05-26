document.addEventListener('DOMContentLoaded', function() {
    // Xử lý trường hợp Ngân hàng khác
    const bankNameSelect = document.getElementById('new_bank_name');
    const otherBankGroup = document.getElementById('otherBankGroup');

    // Khi chọn ngân hàng thay đổi
    bankNameSelect.addEventListener('change', function() {
        if (this.value === 'Ngân hàng khác') {
            otherBankGroup.classList.remove('d-none');
        } else {
            otherBankGroup.classList.add('d-none');
        }
    });

    // Khởi tạo trạng thái ban đầu
    if (bankNameSelect.value === 'Ngân hàng khác') {
        otherBankGroup.classList.remove('d-none');
    } else {
        otherBankGroup.classList.add('d-none');
    }

    // Validate form trước khi submit
    const bankAccountForm = document.getElementById('bankAccountForm');
    if (bankAccountForm) {
        bankAccountForm.addEventListener('submit', function(e) {
            let isValid = true;
            let errorMessage = '';

            // Kiểm tra ngân hàng
            if (!bankNameSelect.value) {
                isValid = false;
                errorMessage += 'Vui lòng chọn ngân hàng\n';
            }

            // Kiểm tra ngân hàng khác
            if (bankNameSelect.value === 'Ngân hàng khác') {
                const otherBankInput = document.getElementById('new_other_bank_name');
                if (!otherBankInput.value.trim()) {
                    isValid = false;
                    errorMessage += 'Vui lòng nhập tên ngân hàng khác\n';
                }
            }

            // Kiểm tra tên chủ tài khoản
            const accountNameInput = document.getElementById('new_account_name');
            if (!accountNameInput.value.trim()) {
                isValid = false;
                errorMessage += 'Vui lòng nhập tên chủ tài khoản\n';
            }

            // Kiểm tra số tài khoản
            const accountNumberInput = document.getElementById('new_account_number');
            if (!accountNumberInput.value.trim()) {
                isValid = false;
                errorMessage += 'Vui lòng nhập số tài khoản\n';
            } else if (!/^\d+$/.test(accountNumberInput.value)) {
                isValid = false;
                errorMessage += 'Số tài khoản chỉ được chứa các chữ số\n';
            }

            if (!isValid) {
                e.preventDefault();
                alert('Vui lòng điền đầy đủ thông tin:\n' + errorMessage);
            }
        });
    }
});
