import { useState } from "react";

function App() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("");

  const uploadVideo = async () => {
    if (!file) {
      alert("Please select a video file");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setStatus("Uploading...");

    try {
      const res = await fetch("http://127.0.0.1:8000/upload", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      setStatus(`Upload successful! Job ID: ${data.job_id}`);
    } catch (err) {
      setStatus("Upload failed");
    }
  };

  return (
    <div style={{ padding: "40px", fontFamily: "Arial" }}>
      <h1>Clueso Clone</h1>

      <input
        type="file"
        accept="video/mp4"
        onChange={(e) => setFile(e.target.files[0])}
      />

      <br /><br />

      <button onClick={uploadVideo}>Upload Video</button>

      <p>{status}</p>
    </div>
  );
}

export default App;
