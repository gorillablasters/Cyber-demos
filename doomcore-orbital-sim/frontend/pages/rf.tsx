import DoomHeader from "../components/DoomHeader";
import Waterfall from "../components/Waterfall";
import SystemGrid from "../components/SystemGrid";

export default function RF() {
  return (
    <>
      <DoomHeader />
      <SystemGrid>
        <div style={{ gridColumn: "span 12" }}>
          <Waterfall />
        </div>
      </SystemGrid>
    </>
  );
}
