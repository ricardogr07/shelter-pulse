describe("ShelterPulse smoke", () => {
  it("home page loads and shows the product name", () => {
    cy.visit("/");
    cy.contains("ShelterPulse").should("be.visible");
  });
});
