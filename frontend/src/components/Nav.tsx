import { Link } from "react-router-dom";

export default function Nav() {
  return (
    <nav>
      <Link to="/">Voku</Link>

      <div>
        <span>Fitness</span>
        <Link to="/fitness/log">Log</Link>
        <Link to="/fitness/history">History</Link>
      </div>

      <div>
        <span>Finance</span>
        <Link to="/finance/import">Import</Link>
        <Link to="/finance/transactions">Transactions</Link>
        <Link to="/finance/summary">Summary</Link>
      </div>
    </nav>
  );
}
