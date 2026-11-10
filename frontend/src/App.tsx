import { useEffect, useState } from "react";
import "./App.css";
import { SearchPage } from "./pages/SearchPage";
import { ReviewPage } from "./pages/ReviewPage";
import { MonitoringPage } from "./pages/MonitoringPage";

function getRoute(): string {
  return window.location.hash.replace("#", "") || "search";
}

function App() {
  const [route, setRoute] = useState(getRoute());

  useEffect(() => {
    const onHash = () => setRoute(getRoute());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  return (
    <div className="app">
      <header className="header">
        <div className="container">
          <nav>
            <a href="#search" className={route === "search" ? "active" : ""}>Search</a>
            <a href="#review" className={route === "review" ? "active" : ""}>Review queue</a>
            <a href="#monitoring" className={route === "monitoring" ? "active" : ""}>Monitoring</a>
          </nav>
        </div>
      </header>
      <main className="container main">
        {route === "search" && <SearchPage />}
        {route === "review" && <ReviewPage />}
        {route === "monitoring" && <MonitoringPage />}
      </main>
    </div>
  );
}

export default App;
