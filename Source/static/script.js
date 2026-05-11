navigator.mediaDevices.getUserMedia({ video: true }).then(stream => {
    document.getElementById('video').srcObject = stream;
  });
  
  document.getElementById("att-form").addEventListener("submit", async function (e) {
    e.preventDefault();
    const roll = document.getElementById("roll").value;
    
    // Capture GPS
    navigator.geolocation.getCurrentPosition(async (position) => {
      const gps = `${position.coords.latitude},${position.coords.longitude}`;
      
      // Capture Image
      const canvas = document.createElement("canvas");
      canvas.width = 320;
      canvas.height = 240;
      const context = canvas.getContext("2d");
      context.drawImage(document.getElementById("video"), 0, 0, 320, 240);
      const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg'));
  
      const formData = new FormData();
      formData.append("roll", roll);
      formData.append("gps", gps);
      formData.append("image", blob);
  
      const res = await fetch("/submit", { method: "POST", body: formData });
      const msg = await res.text();
      alert(msg);
    });
  });
  