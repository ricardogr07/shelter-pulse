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
