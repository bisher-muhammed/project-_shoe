console.log("wishlist.js file loaded successfully!");

$(document).ready(function() {
    console.log("wishlist.js DOM ready");

    // Event delegation for add to wishlist buttons
    $(document).on('click', '.add-to-wishlist-btn', function(e) {
        e.preventDefault();
        
        const $button = $(this);
        const productId = $button.data('product-id');
        
        console.log("Adding Product ID:", productId);
        
        if (!productId) {
            console.error("No product ID found");
            showMessage("Error: No product ID found", 'error');
            return;
        }
        
        // Disable button during request
        $button.prop('disabled', true);
        const originalHtml = $button.html();
        $button.html('<i class="fas fa-spinner fa-spin"></i> Adding...');
        
        // AJAX request to add to wishlist
        $.ajax({
            url: `/add_wishlist/${productId}/`,
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            success: function(response) {
                console.log("Add AJAX Success:", response);
                
                if (response.success) {
                    // Change button to "Added to Wishlist" status (no remove functionality)
                    $button.removeClass('btn-outline-danger add-to-wishlist-btn')
                           .addClass('btn-success')
                           .prop('disabled', true)
                           .css('pointer-events', 'none');
                    $button.html('<i class="fas fa-heart"></i> Added to Wishlist');
                    
                    // Show appropriate message
                    if (response.already_in_wishlist) {
                        showMessage('Product is already in your wishlist.', 'info');
                    } else {
                        showMessage('Product added to wishlist successfully.', 'success');
                    }
                } else {
                    $button.html(originalHtml);
                    showMessage(response.message || 'Error adding to wishlist', 'error');
                }
            },
            error: function(xhr, status, error) {
                console.error("Add AJAX Error:", {xhr, status, error});
                
                $button.html(originalHtml);
                
                if (xhr.status === 401 || xhr.status === 403) {
                    showMessage('Please login to add items to wishlist', 'error');
                    setTimeout(() => {
                        window.location.href = '/login/';
                    }, 1500);
                } else {
                    showMessage('Error adding to wishlist. Please try again.', 'error');
                }
            },
            complete: function() {
                // Re-enable button
                $button.prop('disabled', false);
            }
        });
    });

    // Event delegation for remove from wishlist buttons
    $(document).on('click', '.remove-from-wishlist-btn', function(e) {
        e.preventDefault();
        
        const $button = $(this);
        const productId = $button.data('product-id');
        
        console.log("Removing Product ID:", productId);
        
        if (!productId) {
            console.error("No product ID found");
            showMessage("Error: No product ID found", 'error');
            return;
        }
        
        // Disable button during request
        $button.prop('disabled', true);
        const originalHtml = $button.html();
        $button.html('<i class="fas fa-spinner fa-spin"></i> Removing...');
        
        // AJAX request to remove from wishlist
        $.ajax({
            url: `/remove_wishlist/${productId}/`,
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            success: function(response) {
                console.log("Remove AJAX Success:", response);
                
                if (response.success) {
                    // Change button back to "add to wishlist"
                    $button.removeClass('btn-danger remove-from-wishlist-btn')
                           .addClass('btn-outline-danger add-to-wishlist-btn');
                    $button.html('<i class="far fa-heart"></i> Add to Wishlist');
                    
                    showMessage(response.message || 'Product removed from wishlist successfully.', 'success');
                } else {
                    $button.html(originalHtml);
                    showMessage(response.message || 'Error removing from wishlist', 'error');
                }
            },
            error: function(xhr, status, error) {
                console.error("Remove AJAX Error:", {xhr, status, error});
                
                $button.html(originalHtml);
                showMessage('Error removing from wishlist. Please try again.', 'error');
            },
            complete: function() {
                // Re-enable button
                $button.prop('disabled', false);
            }
        });
    });
});

// Helper function to show messages
function showMessage(message, type) {
    console.log(`Message: ${message}, Type: ${type}`);
    
    // Try to use Bootstrap toast or alert in message container
    if ($('#message-container').length) {
        const alertClass = type === 'success' ? 'alert-success' : 
                          type === 'error' ? 'alert-danger' : 'alert-info';
        
        const alertHtml = `
            <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        
        $('#message-container').html(alertHtml);
        
        // Auto-hide after 4 seconds
        setTimeout(() => {
            $('.alert').fadeOut();
        }, 4000);
    } else {
        // Fallback to simple alert - you can replace this with your preferred notification system
        alert(message);
    }
}