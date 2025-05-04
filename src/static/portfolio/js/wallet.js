/**
 * Wallet management scripts
 */
document.addEventListener('DOMContentLoaded', function() {
    // Handle bank account form logic
    const bankForm = document.getElementById('bankAccountForm');
    if (bankForm) {
        const bankNameSelect = document.getElementById('id_bank_name');
        const otherBankGroup = document.getElementById('otherBankGroup');
        
        // Toggle other bank name field visibility based on selection
        bankNameSelect.addEventListener('change', function() {
            if (this.value === 'other') {
                otherBankGroup.classList.remove('d-none');
                document.getElementById('id_other_bank_name').setAttribute('required', 'required');
            } else {
                otherBankGroup.classList.add('d-none');
                document.getElementById('id_other_bank_name').removeAttribute('required');
            }
        });
        
        // Form validation
        bankForm.addEventListener('submit', function(event) {
            let isValid = true;
            let errorMessages = [];
            
            // Validate bank selection
            if (!bankNameSelect.value) {
                isValid = false;
                errorMessages.push('Vui lòng chọn ngân hàng');
                bankNameSelect.classList.add('is-invalid');
            } else {
                bankNameSelect.classList.remove('is-invalid');
            }
            
            // Validate other bank name if applicable
            if (bankNameSelect.value === 'other') {
                const otherBankInput = document.getElementById('id_other_bank_name');
                if (!otherBankInput.value.trim()) {
                    isValid = false;
                    errorMessages.push('Vui lòng nhập tên ngân hàng khác');
                    otherBankInput.classList.add('is-invalid');
                } else {
                    otherBankInput.classList.remove('is-invalid');
                }
            }
            
            // Validate account name
            const accountName = document.getElementById('id_account_name');
            if (!accountName.value.trim()) {
                isValid = false;
                errorMessages.push('Vui lòng nhập tên chủ tài khoản');
                accountName.classList.add('is-invalid');
            } else {
                accountName.classList.remove('is-invalid');
            }
            
            // Validate account number
            const accountNumber = document.getElementById('id_account_number');
            if (!accountNumber.value.trim()) {
                isValid = false;
                errorMessages.push('Vui lòng nhập số tài khoản');
                accountNumber.classList.add('is-invalid');
            } else {
                accountNumber.classList.remove('is-invalid');
            }
            
            // Demo purposes only - always display success message
            if (true) { // change this condition if you want to simulate form validation
                event.preventDefault();
                alert('Đã thêm tài khoản ngân hàng thành công! (Đây là thông báo demo)');
                window.location.href = 'bank_accounts.html';
            }
        });
    }
});