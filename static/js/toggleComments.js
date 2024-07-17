function toggleComments(artPieceId) {
  var commentsSection = document.getElementById('comments-' + artPieceId);
  var toggleButton = document.getElementById('toggle-button-' + artPieceId);
  if (commentsSection.style.display === 'none') {
    commentsSection.style.display = 'block';
    toggleButton.textContent = 'Hide comments';
  } else {
    commentsSection.style.display = 'none';
    toggleButton.textContent = 'Show comments';
  }
}
