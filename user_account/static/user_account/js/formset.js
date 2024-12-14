// account/static/account/js/formset.js

$(document).ready(function(){
    var formset = $('#formset');
    var totalForms = $('#id_barber_services-TOTAL_FORMS');
    var formNum = parseInt(totalForms.val());

    $('#add-form').click(function(e){
        e.preventDefault();
        var newForm = $('#empty-form').html().replace(/__prefix__/g, formNum);
        formset.append(newForm);
        totalForms.val(++formNum);
    });
});

