import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { ProgressProvider } from "./progress";
import { Overview } from "./pages/Overview";
import { TrackPage } from "./pages/TrackPage";
import { ModulePage } from "./pages/ModulePage";
import { ExercisePage } from "./pages/ExercisePage";
import { MilestonePage } from "./pages/MilestonePage";
import { NotFound } from "./pages/NotFound";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <ProgressProvider>
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/t/:trackId" element={<TrackPage />} />
          <Route path="/t/:trackId/m/:moduleId" element={<ModulePage />} />
          <Route path="/t/:trackId/m/:moduleId/e/:level/:slug" element={<ExercisePage />} />
          <Route path="/t/:trackId/capstone/:milestoneId" element={<MilestonePage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </ProgressProvider>
    </BrowserRouter>
  </StrictMode>,
);
