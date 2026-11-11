import React, { useState, useEffect, useRef } from "react";
import AuthForm from "./components/AuthForm";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import ChatArea from "./components/ChatArea";
import UploadModal from "./components/UploadModal";
import Notification from "./components/Notification";

const API_BASE_URL = "http://localhost:8000/api";

const App = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [token, setToken] = useState(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [authMode, setAuthMode] = useState("login");

  const [collections, setCollections] = useState([]);
  const [selectedCollection, setSelectedCollection] = useState(null);
  const [messages, setMessages] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [insights, setInsights] = useState(null);
  const [showUploadModal, setShowUploadModal] = useState(false);

  const [uploadFiles, setUploadFiles] = useState([]);
  const [collectionName, setCollectionName] = useState("");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [notification, setNotification] = useState(null);

  const fileInputRef = useRef(null);

  const showNotification = (message, type = "success") => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 4000);
  };

  useEffect(() => {
    const savedToken = localStorage.getItem("voilet_token");
    const savedUsername = localStorage.getItem("voilet_username");
    if (savedToken && savedUsername) {
      setToken(savedToken);
      setUsername(savedUsername);
      setIsAuthenticated(true);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated && token) {
      fetchCollections();
    }
  }, [isAuthenticated, token]);

  const handleAuth = async () => {
    if (!username || !password) {
      showNotification("Please enter username and password", "error");
      return;
    }
    setIsLoading(true);
    try {
      const endpoint = authMode === "login" ? "/auth/login" : "/auth/register";
      let resp;

      if (authMode === "login") {
        // OAuth2PasswordRequestForm expects x-www-form-urlencoded
        const body = new URLSearchParams({ username, password }).toString();
        resp = await fetch(`${API_BASE_URL}${endpoint}`, {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body,
        });
      } else {
        // Register expects JSON body
        resp = await fetch(`${API_BASE_URL}${endpoint}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password }),
        });
      }
      const data = await resp.json();
      if (resp.ok) {
        if (authMode === "login") {
          setToken(data.access_token);
          localStorage.setItem("voilet_token", data.access_token);
          localStorage.setItem("voilet_username", username);
          setIsAuthenticated(true);
          showNotification("Welcome back!");
          // open upload modal automatically after first login — makes it easy to try the app
          setShowUploadModal(true);
        } else {
          showNotification("Account created! Please login.");
          setAuthMode("login");
          setPassword("");
        }
      } else {
        showNotification(data.detail || "Authentication failed", "error");
      }
    } catch {
      showNotification("Connection error. Please try again.", "error");
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    setToken(null);
    setUsername("");
    setPassword("");
    localStorage.removeItem("voilet_token");
    localStorage.removeItem("voilet_username");
    localStorage.removeItem("voilet_collection_id");
    setCollections([]);
    setSelectedCollection(null);
    setMessages([]);
    showNotification("Logged out successfully");
  };

  const fetchCollections = async () => {
    try {
      const resp = await fetch(`${API_BASE_URL}/app/collections`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (resp.ok) {
        const data = await resp.json();
        setCollections(data);
        const savedCollectionId = Number(localStorage.getItem("voilet_collection_id"));
        const collectionToRestore =
          data.find((collection) => collection.id === savedCollectionId) || data[0];
        if (collectionToRestore) {
          handleSelectCollection(collectionToRestore);
        }
      }
    } catch (err) {
      console.error("Error fetching collections:", err);
    }
  };

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    const pdfFiles = files.filter((f) => f.name.toLowerCase().endsWith(".pdf"));
    if (pdfFiles.length !== files.length) {
      showNotification("Only PDF files are supported", "error");
    }
    setUploadFiles(pdfFiles);
  };

  const handleUpload = async () => {
    if (uploadFiles.length === 0 || !collectionName.trim()) {
      showNotification("Please select files and enter a collection name", "error");
      return;
    }
    setIsLoading(true);
    setUploadProgress(10);
    const formData = new FormData();
    uploadFiles.forEach((file) => formData.append("files", file));
    formData.append("collection_name", collectionName);
    formData.append("llm_provider", "gemini");
    formData.append("llm_model", "gemini-3.8-flash");
    try {
      setUploadProgress(30);
      const resp = await fetch(`${API_BASE_URL}/app/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      setUploadProgress(70);
      const data = await resp.json();
      if (resp.ok) {
        setUploadProgress(100);
        showNotification(`Successfully uploaded ${uploadFiles.length} file(s)!`);
        setShowUploadModal(false);
        setUploadFiles([]);
        setCollectionName("");
        setUploadProgress(0);
        await fetchCollections();
        setSelectedCollection(data.collection);
        if (data.insights) {
          setInsights(data.insights);
        }
      } else {
        showNotification(data.detail || "Upload failed", "error");
      }
    } catch {
      showNotification("Upload error. Please try again.", "error");
    } finally {
      setIsLoading(false);
      setUploadProgress(0);
    }
  };

  const handleSelectCollection = async (collection) => {
    setSelectedCollection(collection);
    localStorage.setItem("voilet_collection_id", String(collection.id));
    setMessages([]);
    setInsights(null);
    try {
      const resp = await fetch(`${API_BASE_URL}/app/insights/${collection.id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (resp.ok) {
        const data = await resp.json();
        setInsights(data.insights);
      }
      const messagesResp = await fetch(`${API_BASE_URL}/app/collections/${collection.id}/messages`, {
        headers: { Authorization: "Bearer " + token },
      });
      if (messagesResp.ok) {
        const history = await messagesResp.json();
        setMessages(history.map((message) => ({
          role: message.role,
          content: message.content,
          sources: message.sources,
          type: message.type,
        })));
      }
    } catch (err) {
      console.error("Error fetching collection data:", err);
    }
  };

  const handleSendQuestion = async (question = currentQuestion) => {
    if (!question.trim() || !selectedCollection) return;
    const userMessage = { role: "user", content: question };
    setMessages((prev) => [...prev, userMessage]);
    setCurrentQuestion("");
    setIsLoading(true);
    try {
      const resp = await fetch(`${API_BASE_URL}/app/chat`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          collection_id: selectedCollection.id,
          question,
        }),
      });
      const data = await resp.json();
      if (resp.ok) {
        const assistantMessage = {
          role: "assistant",
          content: data.answer,
          sources: data.sources,
          type: data.type,
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } else {
        showNotification(data.detail || "Failed to get answer", "error");
      }
    } catch {
      showNotification("Error sending question", "error");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteCollection = async (collectionId) => {
    if (!window.confirm("Are you sure you want to delete this collection?")) return;
    try {
      const resp = await fetch(`${API_BASE_URL}/app/collections/${collectionId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (resp.ok) {
        showNotification("Collection deleted");
        await fetchCollections();
        if (selectedCollection?.id === collectionId) {
          setSelectedCollection(null);
          setMessages([]);
          setInsights(null);
        }
      }
    } catch {
      showNotification("Error deleting collection", "error");
    }
  };

  if (!isAuthenticated) {
    return (
      <AuthForm
        username={username}
        password={password}
        setUsername={setUsername}
        setPassword={setPassword}
        authMode={authMode}
        setAuthMode={setAuthMode}
        handleAuth={handleAuth}
        isLoading={isLoading}
      />
    );
  }

  return (
    <div className="app-shell flex flex-col bg-slate-50">
      <Notification notification={notification} />
      <Header
        username={username}
        onUploadClick={() => setShowUploadModal(true)}
        onLogout={handleLogout}
      />
      <div className="flex min-h-0 flex-1 overflow-hidden">
        <Sidebar
          collections={collections}
          selectedCollection={selectedCollection}
          onSelect={handleSelectCollection}
          onDelete={handleDeleteCollection}
        />
        <ChatArea
          selectedCollection={selectedCollection}
          messages={messages}
          insights={insights}
          isLoading={isLoading}
          currentQuestion={currentQuestion}
          setCurrentQuestion={setCurrentQuestion}
          handleSendQuestion={handleSendQuestion}
        />
      </div>
      <UploadModal
        showUploadModal={showUploadModal}
        setShowUploadModal={setShowUploadModal}
        uploadFiles={uploadFiles}
        setUploadFiles={setUploadFiles}
        collectionName={collectionName}
        setCollectionName={setCollectionName}
        handleUpload={handleUpload}
        fileInputRef={fileInputRef}
        handleFileSelect={handleFileSelect}
        isLoading={isLoading}
        uploadProgress={uploadProgress}
      />
    </div>
  );
};

export default App;
