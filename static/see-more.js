$(document).ready(() => {
    let perPage = 2;
    let current = perPage;

    function updateSeeMore() {
        document.querySelectorAll('.evaluateB-ul .evaluateB-li').forEach((e, i) => {
            if (i <= current) {
                e.style.display = '';
            } else {
                e.style.display = 'none';
            }
        })
    }

    // After page initiated or "See More" button clicked, update the elements
    document.querySelector('.more').addEventListener('click', () => {
        current += perPage;
        updateSeeMore();
    })
    updateSeeMore();
});
