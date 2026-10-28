import { lazy, StrictMode, Suspense } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { ProgressProvider } from "./progress";
import { NotFound } from "./pages/NotFound";
import "./styles.css";

const Overview = lazy(() => import("./pages/Overview").then((page) => ({ default: page.Overview })));
const TrackPage = lazy(() => import("./pages/TrackPage").then((page) => ({ default: page.TrackPage })));
const ModulePage = lazy(() => import("./pages/ModulePage").then((page) => ({ default: page.ModulePage })));
const ExercisePage = lazy(() => import("./pages/ExercisePage").then((page) => ({ default: page.ExercisePage })));
const MilestonePage = lazy(() => import("./pages/MilestonePage").then((page) => ({ default: page.MilestonePage })));

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <ProgressProvider>
        <Suspense>
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/t/:trackId" element={<TrackPage />} />
            <Route path="/t/:trackId/m/:moduleId" element={<ModulePage />} />
            <Route path="/t/:trackId/m/:moduleId/e/:level/:slug" element={<ExercisePage />} />
            <Route path="/t/:trackId/capstone/:milestoneId" element={<MilestonePage />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </ProgressProvider>
    </BrowserRouter>
  </StrictMode>,
);
