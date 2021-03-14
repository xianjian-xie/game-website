var div = document.getElementById('tag-box');
function addTag() {
  button = document.createElement('button');
  button.setAttribute("id", "removetag");
  // button.innerHTML = 'X';
  button.innerHTML = document.getElementById("tagname").value;
  // attach onlick event handler to remove button
  button.onclick = removeTag;
  div.appendChild(button);
}

function removeTag() {
  // remove this button and its input
  div.removeChild(this);
}
// attach onclick event handler to add button
document.getElementById('addtag').addEventListener('click', addTag);
// attach onclick event handler to 1st remove button
document.getElementById('removetag').addEventListener('click', removeTag);
