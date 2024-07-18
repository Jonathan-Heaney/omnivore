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

document.addEventListener('DOMContentLoaded', function () {
  var textareas = document.querySelectorAll('.replyTextArea');
  var buttons = document.querySelectorAll('.sendButton');

  buttons.forEach(function (button) {
    button.disabled = true;
  });

  textareas.forEach(function (textarea, index) {
    textarea.addEventListener('input', function () {
      var button = buttons[index];
      if (textarea.value.trim() !== '') {
        button.disabled = false;
      } else {
        button.disabled = true;
      }
    });
  });

  textareas.forEach((textarea) => {
    textarea.addEventListener('input', () => {
      // Reset height to auto to recalculate the scrollHeight
      textarea.style.height = 'auto';
      // Set height to scrollHeight
      textarea.style.height = `${textarea.scrollHeight}px`;
    });

    // Trigger input event to set the initial height
    textarea.dispatchEvent(new Event('input'));
  });
});
