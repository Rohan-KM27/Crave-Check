// Function to validate username
function validateUsername(usernameAvailable) {
    const usernameInput = document.getElementById('username');
    const enteredUsername = usernameInput.value;
    const errorElement = document.getElementById('username-error');

    if (usernameAvailable.includes(enteredUsername)) {
        errorElement.style.display = 'block'; 
        usernameInput.value = ''; 
        usernameInput.focus(); 
        return false; 
    }
    
    errorElement.style.display = 'none'; 
    return true; 
}


