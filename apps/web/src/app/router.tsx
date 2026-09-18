import { Navigate, createBrowserRouter } from "react-router-dom";
import { DashboardPage } from "./DashboardPage";
import { AppShell } from "./AppShell";
import { NotFoundPage } from "./NotFoundPage";
import { LeadDetailPage } from "../features/leads/LeadDetailPage";
import { LeadListPage } from "../features/leads/LeadListPage";
import { NewLeadPage } from "../features/leads/NewLeadPage";
import { InboxPage } from "../features/operations/InboxPage";
import { PublicationsPage } from "../features/operations/PublicationsPage";
import { NewPropertyWizardPage } from "../features/properties/NewPropertyWizardPage";
import { PropertyCommandCenterPage } from "../features/properties/PropertyCommandCenterPage";
import { PropertyDetailPage } from "../features/properties/PropertyDetailPage";
import { PropertyListPage } from "../features/properties/PropertyListPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: "dashboard", element: <DashboardPage /> },
      { path: "leads", element: <LeadListPage /> },
      { path: "leads/new", element: <NewLeadPage /> },
      { path: "leads/:id", element: <LeadDetailPage /> },
      { path: "properties", element: <PropertyListPage /> },
      { path: "properties/new", element: <NewPropertyWizardPage /> },
      { path: "properties/:id", element: <PropertyDetailPage /> },
      { path: "properties/:id/command-center", element: <PropertyCommandCenterPage /> },
      { path: "publications", element: <PublicationsPage /> },
      { path: "inbox", element: <InboxPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);
