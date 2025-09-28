// models/Summary.js
const mongoose = require('mongoose');

const SummarySchema = new mongoose.Schema({
  title: { type: String, default: 'Untitled' },
  content: { type: String, required: true },
  created_at: { type: Date, default: Date.now }
});

module.exports = mongoose.model('Summary', SummarySchema);
