function hiddenshow() {
 var selectBox = document.getElementById("selectBox");
 var popuList = document.getElementById("popularity_list");
 var ratingList = document.getElementById("rating_list");
 var selectedValue = selectBox.options[selectBox.selectedIndex].value;
 if (selectedValue == "1") {
   popuList.style.display = "block";
   ratingList.style.display = "none";
 }

else if (selectedValue == "2") {
  popuList.style.display = "none";
  ratingList.style.display = "block";
}
}
