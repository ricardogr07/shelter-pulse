describe("ShelterPulse smoke", () => {
  it("home page loads and shows the product name", () => {
    cy.visit("/");
    cy.contains("ShelterPulse").should("be.visible");
  });

  it("demo wizard loads and shows step 1", () => {
    cy.visit("/en/demo");
    cy.contains("Whisker Haven").should("be.visible");
  });

  it("custom builder loads with form inputs", () => {
    cy.visit("/en/simulate");
    cy.get("input").should("have.length.at.least", 5);
  });

  it("how-it-works loads with expandable sections", () => {
    cy.visit("/en/how-it-works");
    cy.contains("Discrete-Event Simulation").should("exist");
  });
});

// Live-data checks: exercise the two data-dependent pages against a real
// backend, not just DOM-shell presence. Skipped by default - ci.yml's
// per-PR "UI checks" job runs this whole spec file against a local static
// build with no backend (npx serve, no API), so these must stay off there.
// Only deploy.yml's smoke-test-ui job passes --env liveSmoke=true, pointed
// at --config baseUrl=https://shelter-pulse.com (a real deployed backend).
const liveSmoke = Cypress.env("liveSmoke") === true || Cypress.env("liveSmoke") === "true";
(liveSmoke ? describe : describe.skip)("ShelterPulse smoke - live data", () => {
  it("demo wizard: baseline -> optimize renders real computed results", () => {
    cy.visit("/en/demo");
    // Step 1 configure -> baseline (POST /simulate, sync/fast)
    cy.contains("button", "Run Baseline").click();
    cy.contains("Overflow Cat-Days", { timeout: 15000 }).should("be.visible");
    // Step 2 baseline -> bottleneck (no API call)
    cy.contains("button", "See bottlenecks").click();
    // Step 3 bottleneck -> optimize (POST /optimize, cached for demo params, fast)
    cy.contains("button", "Optimize Budget").click();
    // Step 4: real BO winner rendered, not stuck on "Optimizing..."
    cy.contains("Optimized Allocation", { timeout: 30000 }).should("be.visible");
    cy.contains("Overflow Cat-Days").should("be.visible");
  });

  it("custom builder: optimize dispatches the async job and renders real results", () => {
    cy.visit("/en/simulate");
    // Default form values are fine - triggers POST /optimize/builder, which is
    // always async (202 + job_id) in production. The UI's own SSE-driven
    // ProgressStream must resolve to real results within the same window
    // prod sweeps take (~30s-3min, see docs/architecture/async-workers.md).
    cy.contains("button", "Optimize").click();
    cy.contains("Optimization Results", { timeout: 240000 }).should("be.visible");
    // First result row has a real (non-empty) overflow number, not a placeholder
    cy.get("table tbody tr").first().find("td").eq(5).invoke("text").should("match", /\d/);
  });
});
