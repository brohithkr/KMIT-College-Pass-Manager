const video = document.getElementById('video');
const constraints = {
    video: {
        facingMode: "environment"
    }
};

navigator.mediaDevices.getUserMedia(constraints)
    .then(function (stream) {
        video.srcObject = stream;
        video.play();
    })
    .catch(function (err) {
        console.log("An error occurred: " + err);
    });

var v = document.getElementById("video");
v.addEventListener("loadedmetadata", function (e) {
    var width = this.videoWidth,
        height = this.videoHeight;
    var canvas = document.querySelector("#canvas");
    canvas.setAttribute("width", width);
    canvas.setAttribute("height", height);
}, false);

function captureSnapshot() {
    var canvas = document.querySelector("#canvas");
    var context = canvas.getContext('2d');
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    displayShot()
    // console.log(video.width);
    return canvas.toDataURL();
}

function displayShot() {
    document.getElementById("video").style.opacity = 0;
    document.getElementById("canvas").style.opacity = 1;
}
function displayVideo() {
    document.getElementById("video").style.opacity = 1;
    document.getElementById("canvas").style.opacity = 0;
}

let nextbutton = document.getElementById("next");
nextbutton.onclick = function () {
    let modalbox = document.querySelector(".modal");
    modalbox.style.display = "none";
    document.querySelector(".history-list").innerHTML = "";
    displayVideo();
    document.getElementById("errortext").style.display = "none";
}

// console.log(document.cookie)
function getcredentials() {
    var lst = document.cookie.split(";");
    // var uid, pwd;
    var uid = lst[0].split("=")[1];  
    var pwd = lst[1].split("=")[1];
    for (let i = 0; i < lst.length; i++) {
        if (lst[i].split("=")[0] == "uid") {
            uid = lst[i].split("=")[1];
        }
        if (lst[i].split("=")[0] == "pwd") {
            pwd = lst[i].split("=")[1];
        }
    }
    return [uid, pwd];
}

    function displayPopup(isValid, message, history_list) {
        let ticksvg = '<svg id="Layer_1" data-name="Layer 1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 122.88 122.88"><defs><style>.cls-1{fill:#00a912;}.cls-1,.cls-2{fill-rule:evenodd;}.cls-2{fill:#fff;}</style></defs><title>confirm</title><path class="cls-1" d="M61.44,0A61.44,61.44,0,1,1,0,61.44,61.44,61.44,0,0,1,61.44,0Z"/><path class="cls-2" d="M42.37,51.68,53.26,62,79,35.87c2.13-2.16,3.47-3.9,6.1-1.19l8.53,8.74c2.8,2.77,2.66,4.4,0,7L58.14,85.34c-5.58,5.46-4.61,5.79-10.26.19L28,65.77c-1.18-1.28-1.05-2.57.24-3.84l9.9-10.27c1.5-1.58,2.7-1.44,4.22,0Z"/></svg>'
        let crosssvg = '<svg id="Layer_1" data-name="Layer 1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 122.88 122.88"><defs><style>.cls-1{fill:#f44336;fill-rule:evenodd;}</style></defs><title>close-red</title><path class="cls-1" d="M61.44,0A61.44,61.44,0,1,1,0,61.44,61.44,61.44,0,0,1,61.44,0ZM74.58,36.8c1.74-1.77,2.83-3.18,5-1l7,7.13c2.29,2.26,2.17,3.58,0,5.69L73.33,61.83,86.08,74.58c1.77,1.74,3.18,2.83,1,5l-7.13,7c-2.26,2.29-3.58,2.17-5.68,0L61.44,73.72,48.63,86.53c-2.1,2.15-3.42,2.27-5.68,0l-7.13-7c-2.2-2.15-.79-3.24,1-5l12.73-12.7L36.35,48.64c-2.15-2.11-2.27-3.43,0-5.69l7-7.13c2.15-2.2,3.24-.79,5,1L61.44,49.94,74.58,36.8Z"/></svg>'
        let modalbox = document.querySelector(".modal");
        let messagebox = document.querySelector(".message");
        if (isValid == true) {
            document.querySelector(".tickmark").innerHTML = ticksvg;
        }
        else if (isValid == false) {
            document.querySelector(".tickmark").innerHTML = crosssvg;
        }
        var hs = document.querySelector(".history-list");
        var heading = `<tr>
        <th>Time</th>
        <th>Scanned By</th>
    </tr>`
        if (history_list.length < 1){
            heading = ""
        }

        for(let i=0; i< history_list.length; i++){
            // let htmlstr = "<li>" + history[i][0] + "-" +  history[i][1] + "</li>";
            // console.log(history)
            datetime = history_list[i][0]
            hs.innerHTML += `<tr><td>${datetime}</td><td>${history_list[i][1]}</td><tr>`
        }
        // hs.innerHTML += htmlstr;
        // console.log(htmlstr);
        messagebox.innerHTML = message;
        modalbox.style.display = "block";
    }
// var history_list = [["10:45pm 12 Jul, 2023","bobsmith"],["4:45pm 12 Jul, 2023","bobsmith"]]
// console.log(history_list[0])
// displayPopup("none","testing",history_list);

async function isqrvalid(imageBase64, key) {

    let response = await fetch("/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ "b64qr": imageBase64, "key": key })
    })
    let data = await response.json();
    return data;

}

async function verify_sign(uid,pwd,imageBase64) {
    let response = await fetch("/api/verify_sign", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            "uid": uid,
            "pwd": pwd,
            "data": imageBase64
            })
        }
    )
    let data = await response.json();
    return data;
}

async function audit_scan(uid,pwd,rno) {
    let response = await fetch("/api/audit_scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            "uid": uid,
            "pwd": pwd,
            "rno": rno
            })
        }
    )
    let data = await response.json();
    return data;
}


async function get_scan_history(uid,pwd,rno) {
    let response = await fetch("/api/get_scan_history", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            "uid": uid,
            "pwd": pwd,
            "rno": rno
            })
        }
    )
    let data = await response.json();
    return data;
}

async function all_tasks(uid,pwd,imageBase64) {
    let unSignedData = await verify_sign(uid,pwd,imageBase64);
    if (unSignedData["isValidSign"] == false) {
        return {"success": false, "message": unSignedData["failure_reason"]}
    }
    let history = await get_scan_history(uid,pwd,unSignedData["rno"]);
    let audit = await audit_scan(uid,pwd,unSignedData["rno"]);
    if (audit["success"] == false) {
        return {"success": false, "message": audit["msg"], "history": history["history"]}
    }
    return {"success": true, "message": "Pass scanned", "history": history["history"]}
}




document.querySelector("#snap").onclick =  function() {
    document.querySelector(".loadmodal").style.display = "block";
    var imageBase64 = captureSnapshot().replace("data:image/png;base64,", "");
    document.getElementById("errortext").style.display = "none";
    let [uid, pwd] = getcredentials();
    // [uid, pwd] = ["bobsmith", "password456"]
    console.log(uid,pwd);
    // console.log(imageBase64);
    all_tasks(uid,pwd,imageBase64).then(
        (response) => {
            document.querySelector(".loadmodal").style.display = "none";
            // console.log(response);
            if (response["success"] == true) {
                displayPopup(true, response["message"], response["history"]);
            }
            else {
                if (response["history"] != null) {
                    displayPopup(false, response["message"], response["history"]);
                }
                else {
                    errortext = document.getElementById("errortext");
                    errortext.innerHTML = `${response["message"]}`;
                    errortext.style.display = "block";
                }
            }
            displayVideo();
        }
    )

    



    // let uid = "bobsmith";
    // let pwd = "password123"

    // verify_sign(uid,pwd,imageBase64)
    // .then(
    //     unSignedData => {
    //         if (unSignedData["isValidSign"] == true) {
    //             get_scan_history(uid,pwd,unSignedData["rno"])
    //             .then(
    //                 (history) => {
    //                     audit_scan(uid,pwd,unSignedData["rno"]).then(
    //                         (audit) => {
    //                             if (audit["success"] == true) {

    //                             }
    //                         }
    //                     )
    //                 }
    //             )
    //         }
    //     }
    // )

    // if (unSignedData["isValidSign"] == true) {

    // ).then(
    //     response => response.json()
    // ).then (
    //     data => {
    //         document.querySelector(".loadmodal").style.display = "none";
    //         if (data["isValidSign"] == true) {
    //             msg = `${data["isValidSign"]} ${data["rno"]} ${data["failure_reason"]}`;
    //             displayPopup(true, msg);
    //         }
    //         else {
                // errortext = document.getElementById("errortext");
                // errortext.innerHTML = `${data["failure_reason"]}`;
                // errortext.style.display = "block";
    //         }
    //         displayVideo();
    //     }
    // )
    // displayVideo();



}

// document.querySelector("#snap").onclick = function () {
//     document.querySelector(".loadmodal").style.display = "block";
//     var imageBase64 = captureSnapshot().replace("data:image/png;base64,", "");
//     document.getElementById("errortext").style.display = "none";
//     let key = getpass();
//     isqrvalid(imageBase64, key).then(
//         data => {
//             document.querySelector(".loadmodal").style.display = "none";
//             if (data["isValid"] == null) {
//                 displayVideo()
                // errortext = document.getElementById("errortext");
                // errortext.innerHTML = data["message"];
                // errortext.style.display = "block";
//             }
//             else {
//                 errortext = document.getElementById("errortext");
//                 errortext.style.display = "None";
//                 displayShot();
//                 displayPopup(data["isValid"], data["message"]);

//             }
//         }
//     )

// };