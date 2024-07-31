function toggleComments(artPieceId, recipientId) {
  var commentsSection = document.getElementById(
    'comments-' + artPieceId + '-' + recipientId + '-container'
  );
  var toggleButton = document.getElementById(
    'toggle-button-' + artPieceId + '-' + recipientId
  );
  if (commentsSection.style.display === 'none') {
    commentsSection.style.display = 'block';
    toggleButton.innerHTML = '<i class="fa-solid fa-minus"></i>';
  } else {
    commentsSection.style.display = 'none';
    toggleButton.innerHTML = '<i class="fa-solid fa-plus"></i>';
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

function clearForm(form) {
  form.reset();
  button = form.querySelector('.sendButton');
  button.disabled = true;
}

function confirmDelete() {
  return confirm(
    'Are you sure you want to delete this post? This cannot be undone.'
  );
}

// Modal handling
document.addEventListener('DOMContentLoaded', function () {
  // Function to open the modal
  function openModal(modalId) {
    document.getElementById(modalId).style.display = 'block';
  }

  // Function to close the modal
  function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
  }

  // Add event listeners to all open modal links
  document.querySelectorAll('.open-modal').forEach(function (element) {
    element.addEventListener('click', function (event) {
      event.preventDefault(); // Prevent default action that causes scrolling
      const modalId = event.target.getAttribute('data-modal-id');
      openModal(modalId);
    });
  });

  // Add event listeners to all close modal spans
  document.querySelectorAll('.modal .close').forEach(function (element) {
    element.addEventListener('click', function () {
      const modalId = element.getAttribute('data-modal-id');
      closeModal(modalId);
    });
  });

  // Close the modal when clicking outside of the modal content
  window.addEventListener('click', function (event) {
    document.querySelectorAll('.modal').forEach(function (modal) {
      if (event.target == modal) {
        modal.style.display = 'none';
      }
    });
  });
});

function toggleHeartIcon(event) {
  event.preventDefault();

  // Find the button that was clicked
  const button = event.target.querySelector('button.like-button');

  // Toggle the "liked" class immediately
  button.classList.toggle('liked');

  // Let HTMX handle the form submission in the background
  event.target.submit();
}
