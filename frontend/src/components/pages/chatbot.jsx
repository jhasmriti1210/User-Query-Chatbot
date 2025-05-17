import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import { Send, Mic, Volume2, VolumeX, UploadCloud } from "lucide-react";

import "./chatbot.css";

export default function Chat() {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [muted, setMuted] = useState(false);
  const [listening, setListening] = useState(false);
  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);
  const [file, setFile] = useState(null);
  const [uploadedFilename, setUploadedFilename] = useState(null);

  // Fixed language (removed selector)
  const language = "en-US";

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!message.trim() || loading) return;

    if (!uploadedFilename) {
      alert("Please upload a PDF file first!");
      return;
    }

    setMessages((prev) => [...prev, { role: "user", text: message }]);
    setLoading(true);
    setMessage("");

    try {
      const { data } = await axios.post(
        "http://localhost:8080/query",
        {
          question: message,
          filename: uploadedFilename,
          language,
        },
        { headers: { "Content-Type": "application/json" } }
      );

      const responseText = data.answer || "No answer returned.";
      setMessages((prev) => [...prev, { role: "bot", text: responseText }]);
      if (!muted) speakText(responseText);
    } catch (error) {
      console.error("Error:", error);
      setMessages((prev) => [
        ...prev,
        { role: "bot", text: "⚠️ Unable to connect. Try again." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const speakText = (text) => {
    if (!window.speechSynthesis || muted) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = language;
    window.speechSynthesis.speak(utterance);
  };

  const startListening = () => {
    if (!("webkitSpeechRecognition" in window)) {
      alert("Speech recognition is not supported in your browser.");
      return;
    }

    if (!recognitionRef.current) {
      const recognition = new window.webkitSpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = language;

      recognition.onstart = () => setListening(true);
      recognition.onend = () => setListening(false);
      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setMessage(transcript);
      };
      recognition.onerror = (event) => console.error("Speech error:", event);

      recognitionRef.current = recognition;
    }

    recognitionRef.current.lang = language;
    recognitionRef.current.start();
  };

  const handleFileUpload = async () => {
    if (!file) return;
    setLoading(true);
    setMessages((prev) => [
      ...prev,
      { role: "user", text: `📎 Uploaded file: ${file.name}` },
    ]);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const { data } = await axios.post(
        "http://localhost:8080/upload",
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
        }
      );

      if (data.filename) {
        setUploadedFilename(data.filename);
        setMessages((prev) => [
          ...prev,
          { role: "bot", text: `File uploaded and indexed: ${data.filename}` },
        ]);
      } else if (data.message) {
        setMessages((prev) => [...prev, { role: "bot", text: data.message }]);
      }
      if (!muted && data.message) speakText(data.message);
      setFile(null);
    } catch (error) {
      console.error("Upload failed:", error);
      setMessages((prev) => [
        ...prev,
        { role: "bot", text: "⚠️ Upload failed. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-box">
        <h2 className="chat-header">
          <img src="/chatbot.png" alt="Bot" className="botimg" />
          AroVeda
        </h2>

        <div className="chat-messages">
          {messages.map((msg, index) => (
            <div key={index} className={`message ${msg.role}`}>
              {msg.role === "bot" && (
                <img src="/chatbot.png" alt="Bot" className="bot-profile" />
              )}
              <div className="message-content">
                <strong>{msg.role === "user" ? "You" : "Bot"}:</strong>{" "}
                {msg.text}
                {msg.role === "bot" && (
                  <button
                    className="icon-button"
                    onClick={() => speakText(msg.text)}
                  >
                    <Volume2 size={18} />
                  </button>
                )}
              </div>
            </div>
          ))}
          {loading && <div className="loading">Typing...</div>}
          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input-section">
          <button onClick={() => setMuted(!muted)} className="icon-button">
            {muted ? <VolumeX size={20} /> : <Volume2 size={20} />}
          </button>

          <button onClick={startListening} className="icon-button">
            <Mic size={20} color={listening ? "red" : "black"} />
          </button>

          <input
            type="text"
            className="chat-input"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder={
              uploadedFilename
                ? "Ask a question about your uploaded PDF..."
                : "Upload a PDF first..."
            }
            disabled={!uploadedFilename || loading}
          />

          <button
            onClick={sendMessage}
            disabled={!message.trim() || loading || !uploadedFilename}
            className="send-button"
          >
            <Send size={20} />
          </button>

          <input
            type="file"
            accept="application/pdf"
            onChange={(e) => setFile(e.target.files[0])}
            disabled={loading}
          />

          <button
            onClick={handleFileUpload}
            disabled={!file || loading}
            className="upload-button"
          >
            <UploadCloud size={20} />
          </button>
        </div>
      </div>
    </div>
  );
}
