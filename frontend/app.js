// app.js

// 🚨 CHANGE: Separate constants for Node.js (API_NODE) and FastAPI (API_FASTAPI)
const API_NODE = "http://localhost:9000/api";
const API_FASTAPI = "http://localhost:8000"; 
let currentUser = null;

// ===================================
// AUTHENTICATION FUNCTIONS
// ===================================
async function login() {
  // 🚨 FIX: Your Node.js server expects 'email' for login, not 'username'
  const email = document.getElementById("username").value; 
  const password = document.getElementById("password").value;
  
  const res = await fetch(`${API_NODE}/login`, { // Use API_NODE
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }) // Use email
  });
  const data = await res.json();
  
  if (res.ok) {
    currentUser = data.user;
    document.getElementById("loginPage").style.display = "none";
    document.getElementById("dashboard").style.display = "block";
    document.getElementById("userRole").innerText = currentUser.role;
    loadDocuments();
  } else {
    document.getElementById("loginMsg").innerText = data.error;
  }
}

function logout() {
  currentUser = null;
  document.getElementById("loginPage").style.display = "block";
  document.getElementById("dashboard").style.display = "none";
}

// ===================================
// DOCUMENT LOADING FUNCTIONS
// ===================================
async function loadDocuments() {
  const res = await fetch(`${API_NODE}/documents`); // Use API_NODE
  const docs = await res.json();
  const list = document.getElementById("docsList");
  list.innerHTML = "";
  docs.forEach(doc => {
    const div = document.createElement("div");
    div.className = "doc-card";
    div.innerText = doc.title + " (by " + doc.uploadedBy + ")";
    div.onclick = () => showDoc(doc);
    list.appendChild(div);
  });
}

// 🚨 CRITICAL FIX: showDoc must render the URL as a clickable link.
function showDoc(doc) {
  document.getElementById("docDetails").style.display = "block";
  document.getElementById("docTitle").innerText = doc.title;
  
  // Get the element where the link will be displayed
  const docUrlElement = document.getElementById("docUrl");
  // Set its innerHTML to a full anchor tag <a>
  docUrlElement.innerHTML = `
    <a href="${doc.url}" target="_blank" class="text-primary hover:underline font-medium">
      Download Summary: ${doc.title}
    </a>
  `;
  
  // The doc.summary field now contains placeholder text saved from the upload function
  document.getElementById("docSummary").innerText = doc.summary;
}

// ===================================
// 🚨 NEW FUNCTION: FILE UPLOAD
// ===================================
async function uploadFile(formElement) {
    const fileInput = formElement.querySelector('#documentFile');
    const titleInput = formElement.querySelector('#documentTitle');
    const file = fileInput.files[0];
    const title = titleInput.value.trim() || file.name;

    if (!file) {
        alert("Please select a file to upload.");
        return;
    }

    try {
        // 1. Upload file to FastAPI for processing
        const formData = new FormData();
        formData.append("file", file);

        const uploadRes = await fetch(`${API_FASTAPI}/upload/`, {
            method: "POST",
            body: formData 
        });

        if (!uploadRes.ok) {
            const errorData = await uploadRes.json();
            throw new Error(`FastAPI Processing Failed: ${errorData.detail || uploadRes.statusText}`);
        }

        const uploadData = await uploadRes.json();
        // Extract the filename from the path returned by FastAPI
        const summaryFileName = uploadData.summary_file.split('/').pop(); 
        
        // Construct the permanent URL using the FastAPI download endpoint
        const permanentSummaryURL = `${API_FASTAPI}/download_summary/${summaryFileName}`;

        // 2. Save document metadata to Node.js/MongoDB
        const docMetadata = {
            title: title,
            url: permanentSummaryURL, 
            summary: "Document processed. Click the link above to view/download the summary.", 
            uploadedBy: currentUser ? currentUser.email : 'guest@system.com' 
        };

        const saveRes = await fetch(`${API_NODE}/documents`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(docMetadata)
        });

        if (!saveRes.ok) {
             const errorData = await saveRes.json();
             throw new Error(`Node.js Save Failed: ${errorData.error || saveRes.statusText}`);
        }

        // 3. Success
        alert(`File "${title}" processed and saved successfully!`);
        formElement.reset(); 
        loadDocuments(); 

    } catch (error) {
        console.error("Upload/Processing Error:", error);
        alert(`Failed to process document: ${error.message}`);
    }
}