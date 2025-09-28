import express from 'express';
import mongoose from 'mongoose';
import jwt from 'jsonwebtoken';
import cors from 'cors';

// Secret key for JWT signing and verification
const JWT_SECRET = 'your_super_secret_jwt_key'; // CHANGE THIS IN PRODUCTION

// --- MongoDB Connection (Ensure this is correct) ---
mongoose.connect("mongodb+srv://Kevin:Year2006@users.s5a3uxi.mongodb.net/?retryWrites=true&w=majority&appName=Users", {
    useNewUrlParser: true,
    useUnifiedTopology: true
})
.then(() => console.log("✅ MongoDB Connected"))
.catch(err => console.error("❌ MongoDB Error:", err));

// --- Schemas and Models ---

// User Schema
const UserSchema = new mongoose.Schema({
    email: { type: String, required: true, unique: true },
    password: { type: String, required: true }, // TODO: hash with bcrypt in production
    role: { type: String, required: true, default: 'employee', enum: ['employee', 'hr', 'admin'] },
    designation: { type: String, required: true }
});
const User = mongoose.model("User", UserSchema);

// Document Schema
const documentSchema = new mongoose.Schema({
    title: { type: String, required: true },
    url: { type: String, default: "" },
    filename: { type: String, default: "" }, // Stores the original file name
    summary: { type: String, default: "" }, // Stores the full summary text
    uploadedBy: { type: String, required: true },
    uploadedAt: { type :Date, default: Date.now },
});
const Document = mongoose.model("Document", documentSchema);

// ---------------------------------
// Express Middleware Configuration
// ---------------------------------
const app = express();

// FIX: Increase body parser limit to ensure long summary text is not truncated
app.use(express.json({ limit: '50mb' })); // Allows large JSON payloads (including summary)
app.use(express.urlencoded({ limit: '50mb', extended: true })); // Handles large URL-encoded payloads

// CORS configuration to allow requests from the frontend (Port 3000/8080/etc.)
app.use(cors({
    origin: '*', // Allows all origins for local development
    methods: ['GET', 'POST', 'PUT', 'DELETE'],
    allowedHeaders: ['Content-Type', 'Authorization']
}));

// ---------------------------------
// API Endpoints
// ---------------------------------

// Middleware for token verification (Not fully implemented, but structure is needed)
const authenticateToken = (req, res, next) => {
    // In a production app, you would check req.headers.authorization
    // For this simple example, we skip actual token validation.
    // However, the client is expected to send the user info directly in the body for /api/documents
    next();
};

// --- AUTHENTICATION & USER ENDPOINTS ---

// Register User
app.post("/api/register", async (req, res) => {
    try {
        const { email, password, role, designation } = req.body; 

        if (!email || !password || !role || !designation) {
             return res.status(400).json({ error: "Missing required fields: email, password, role, or designation." });
        }
        
        const existingUser = await User.findOne({ email });
        if (existingUser) {
            return res.status(409).json({ error: "User with this email already exists." });
        }

        const newUser = new User({ email, password, role, designation });
        await newUser.save();
        res.status(200).json({ message: "User registered successfully." });
    } catch (error) {
        console.error("Registration Error:", error);
        res.status(500).json({ error: "Server error during registration." });
    }
});

// Login User
app.post("/api/login", async (req, res) => {
    try {
        const { email, password } = req.body;
        const user = await User.findOne({ email, password });

        if (!user) {
            return res.status(401).json({ error: "Invalid credentials." });
        }

        // Generate JWT token (not strictly used by the frontend yet, but good practice)
        const token = jwt.sign({ userId: user._id, role: user.role }, JWT_SECRET, { expiresIn: '1h' });

        res.status(200).json({ 
            message: "Login successful.", 
            token,
            user: { 
                email: user.email, 
                role: user.role, 
                designation: user.designation 
            }
        });

    } catch (error) {
        console.error("Login Error:", error);
        res.status(500).json({ error: "Server error during login." });
    }
});

// --- DOCUMENT ENDPOINTS ---

// Get all documents
app.get("/api/documents", async (req, res) => {
    try {
        const documents = await Document.find().sort({ uploadedAt: -1 });
        res.status(200).json(documents);
    } catch (error) {
        console.error("GET Documents Error:", error);
        res.status(500).json({ error: "Failed to retrieve documents." });
    }
});

// Save a new document record (Called AFTER FastAPI summarization)
app.post("/api/documents", async (req, res) => {
    try {
        // --- ADDED LOGGING ---
        console.log("--- DOCUMENT SAVE ATTEMPT ---");
        console.log("Received body:", req.body);
        console.log("-----------------------------");
        
        // Ensure all required fields, including the summary, are extracted
        const { title, url, summary, uploadedBy, filename } = req.body; 
        
        if (!title || !uploadedBy || (!url && !filename)) {
            return res.status(400).json({ error: "Missing required document fields (title, uploader, url/filename)." });
        }

        const newDoc = new Document({ title, url, summary, uploadedBy, filename, uploadedAt: new Date() });
        await newDoc.save();

        res.status(201).json({ message: "Document saved successfully.", document: newDoc });
    } catch (error) {
        console.error("POST Document Save Error:", error);
        res.status(500).json({ error: "Server error while saving document record." });
    }
});

// Delete a document by ID
app.delete("/api/documents/:id", authenticateToken, async (req, res) => {
    try {
        const { id } = req.params;
        const result = await Document.findByIdAndDelete(id);

        if (!result) {
            return res.status(404).json({ error: "Document not found." });
        }

        res.status(200).json({ message: "Document deleted successfully." });
    } catch (error) {
        console.error("DELETE Document Error:", error);
        res.status(500).json({ error: "Server error while deleting document." });
    }
});


// Start server
const PORT = 9000;
app.listen(PORT, () => {
    console.log(`🚀 Express server running on port ${PORT}`);
});
