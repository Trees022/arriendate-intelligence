import { Navigate, createBrowserRouter } from "react-router-dom";
import { DashboardPage } from "./DashboardPage";
import { AppShell } from "./AppShell";
import { NotFoundPage } from "./NotFoundPage";
import { LeadDetailPage } from "../features/leads/LeadDetailPage";
import { NewLeadPage } from "../features/leads/NewLeadPage";
import { PropertyDetailPage } from "../features/properties/PropertyDetailPage";
import { PropertyListPage } from "../features/properties/PropertyListPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: "dashboard", element: <DashboardPage /> },
      { path: "leads/new", element: <NewLeadPage /> },
      { path: "leads/:id", element: <LeadDetailPage /> },
      { path: "properties", element: <PropertyListPage /> },
      { path: "properties/:id", element: <PropertyDetailPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);
