import { BrowserRouter, Routes, Route } from "react-router-dom";
import Shell from "./components/layout/Shell";
import Home from "./pages/Home";
import Log from "./pages/fitness/Log";
import History from "./pages/fitness/History";
import Import from "./pages/finance/Import";
import Transactions from "./pages/finance/Transactions";
import Summary from "./pages/finance/Summary";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Shell />}>
          <Route path="/" element={<Home />} />
          <Route path="/fitness/log" element={<Log />} />
          <Route path="/fitness/history" element={<History />} />
          <Route path="/finance/import" element={<Import />} />
          <Route path="/finance/transactions" element={<Transactions />} />
          <Route path="/finance/summary" element={<Summary />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
