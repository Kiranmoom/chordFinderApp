const express = require("express");
const multer = require("multer");
const path = require("path");
const { exec } = require("child_process");
const fs = require("fs");

const app = express();
const port = 3000;

// Upload config (store files in 'uploads/' directory)
const storage = multer.diskStorage({
  destination: "uploads/",
  filename: (req, file, cb) => {
    cb(null, "upload_" + Date.now() + path.extname(file.originalname));
  },
});
const upload = multer({ storage });

// === POST /upload ===
app.post("/upload", upload.single("audio"), (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: "No file uploaded." });
  }

  const inputPath = req.file.path;

  // Run the Python script
  const pythonScript = `python3 guitarChordFinder.py "${inputPath}"`;

  exec(pythonScript, (error, stdout, stderr) => {
    if (error) {
      console.error("Python script error:");
      console.error(stderr); // Log the actual Python error
  
      return res.status(500).json({
        error: "Python script failed.",
        details: stderr.toString()  // This gives you more info in Postman!
      });
    }
  
    // Return output CSV as JSON
    const csvPath = "detected_chords_clean.csv";
    if (!fs.existsSync(csvPath)) {
      return res.status(404).json({ error: "Chords CSV not found." });
    }

    const csvData = fs.readFileSync(csvPath, "utf8");
    const lines = csvData.trim().split("\n").slice(1); // Skip header
    const chords = lines.map((line) => {
      const [start, end, chord] = line.split(",");
      return { start: parseFloat(start), end: parseFloat(end), chord: chord.trim() };
    });

    res.json({ chords });
  });
});

// Start server
app.listen(port, () => {
  console.log(`API listening at http://localhost:${port}`);
});
