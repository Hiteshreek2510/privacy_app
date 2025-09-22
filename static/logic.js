document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("chat-form");
  const responseContainer = document.getElementById("response");

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const userQuery = document.getElementById("user_query").value;

    // Show user's question
    responseContainer.innerHTML += `
      <div class="chat-bubble user">You asked: ${userQuery}</div>
    `;

    try {
      const res = await fetch("/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: new URLSearchParams({
          user_query: userQuery,
        }),
      });

      const data = await res.text(); // Flask returns HTML, not JSON

      // Replace entire page with new HTML
      document.open();
      document.write(data);
      document.close();
    } catch (error) {
      responseContainer.innerHTML += `
        <div class="chat-bubble bot error">Error: ${error.message}</div>
      `;
    }
  });
});
