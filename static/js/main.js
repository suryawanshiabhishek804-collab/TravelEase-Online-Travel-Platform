document.addEventListener("DOMContentLoaded", () => {
  const dateInputs = document.querySelectorAll('input[type="date"]');
  const today = new Date().toISOString().split("T")[0];
  dateInputs.forEach(input => {
    if (!input.min) input.min = today;
  });
});
