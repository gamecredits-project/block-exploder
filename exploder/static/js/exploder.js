$(function(){
  var $latestBlocksTable = $(".latest-blocks-table");
  var $latestTransactionsTable = $(".latest-transactions-table");
  var $searchButton = $(".js-search-button");
  var $searchInput = $(".js-search-input");
  var $browseBlocksTable = $(".browse-blocks-table");
  var blockTemplate = _.template($(".js-block-template").html());
  var transactionTemplate = _.template($(".js-transaction-template").html());
  var $previousPageLink = $(".js-previous-page");
  var $nextPageLink = $(".js-next-page");
  var $latestBlocksPlaceholder = $(".latest-blocks-placeholder"); 
  var $latestTransactionsPlaceholder = $(".latest-transactions-placeholder"); 
  var $browseBlocksPlaceholder = $(".browse-blocks-placeholder");
  var $blockTransactions = $(".block-transactions");
  var transactionDetailsTemplate = _.template($(".js-transaction-details-template").html());

  var $nodeInformation = $(".node-information");

  var BLOCKS_PER_PAGE = 20;
  var blocksOffset = 0;

  var pathName = window.location.pathname;

  var $headerLinks = $(".main-nav li");

  var exploderStatus = {}
  var halvingEvery = 840000 //blocks;

  $.ajax({
      url: '/network/status',
      type: "get"
    }).done(function(data){
      exploderStatus = data;
      console.log(exploderStatus);

      if($nodeInformation.length > 0) {
        var networkTemplate = _.template($(".js-network-template").html());
        $nodeInformation.append(networkTemplate(data));
      }

      var $syncStatus = $(".js-sync-status");

      var syncPercentage = (exploderStatus.height * 100 / exploderStatus.client.blocks).toFixed(2);

      if(syncPercentage < 100) {
        $syncStatus.html("<span class='text-danger'><i class='fa fa-refresh fa-spin fa-fw'></i>" + syncPercentage + "%</span>");      
      }
      else {
        $syncStatus.html("<span class='text-success'><i class='fa fa-check'></i>" + syncPercentage + "%</span>");      
      }

      var estimatedHalvingDate = moment(1495545484051);
      var $countdownTimer = $(".js-countdown-timer");
      var $cdtDays = $countdownTimer.find(".days");
      var $cdtHours = $countdownTimer.find(".hours");
      var $cdtMinutes = $countdownTimer.find(".minutes");
      var $cdtSeconds = $countdownTimer.find(".seconds");
      var $cdtMilliseconds = $countdownTimer.find(".milliseconds");

      window.setInterval(function(){
        var diff = moment.duration(estimatedHalvingDate - moment());

        var days = Math.floor(diff.asDays());
        var hours = Math.floor(diff.asHours() - days * 24);
        var minutes = Math.floor(diff.asMinutes() - hours * 60 - days * 24 * 60);
        var seconds = Math.floor(diff.asSeconds() - minutes * 60 - hours * 60 * 60 - days * 24 * 60 * 60);
        var milliseconds = Math.floor(diff - seconds * 1000 - minutes * 60 * 1000 - hours * 60 * 60 * 1000 - days * 24 * 60 * 60 * 1000);

        $cdtDays.html(days);
        $cdtHours.html(hours);
        $cdtMinutes.html(minutes);
        $cdtSeconds.html(seconds);
        $cdtMilliseconds.html(milliseconds);

      }, 10);
    }).fail(function(jqXHR, textStatus){
      console.error(textStatus);
    });

  _.each($headerLinks, function(link){
    var linkHref = $(link).find("a").attr("href");
    if(linkHref === pathName) {
      $(link).addClass("active");
    }
  });

  $previousPageLink.click(function(){
    blocksOffset += BLOCKS_PER_PAGE;

    if(exploderStatus && blocksOffset >= exploderStatus.height) {
      $previousPageLink.addClass("disabled");
    }

    $nextPageLink.removeClass("disabled");
    getBlocks(BLOCKS_PER_PAGE, blocksOffset, showBlocks);
  });

  $nextPageLink.click(function(){
    blocksOffset -= BLOCKS_PER_PAGE;

    if(blocksOffset <= 0) {
      $nextPageLink.addClass("disabled");
    }

    $previousPageLink.removeClass("disabled");
    getBlocks(BLOCKS_PER_PAGE, blocksOffset, showBlocks);
  });

  
  if($latestBlocksTable.length > 0){
    window.setInterval(function(){
      $.ajax({
        url: '/blocks/latest',
      }).done(function(data){
          $latestBlocksTable.find("tbody").html("");
          $latestBlocksPlaceholder.remove();
        _.each(data, function(block) {
          block.age = moment.unix(block.time).fromNow();
          $latestBlocksTable.find("tbody").append(blockTemplate(block));
        });
      }).fail(function(jqXHR, textStatus){
        console.error(textStatus);
      });
    }, 60000);
  }

  if($latestTransactionsTable.length > 0) {
    window.setInterval(function(){
      console.log("Refres");
      $.ajax({
        url: '/transactions/latest',
      }).done(function(data){
          $latestTransactionsTable.find("tbody").html("");
          $latestTransactionsPlaceholder.remove();
        _.each(data, function(transaction) {
          transaction.txid_short = transaction.txid.substring(32) + "...";
          $latestTransactionsTable.find("tbody").append(transactionTemplate(transaction));
        });
      }).fail(function(jqXHR, textStatus){
        console.error(textStatus);
      });
    }, 1000);
  }

  function getBlocks(number, offset, callback) {
    $.ajax({
      url: '/blocks',
      type: "get",
        data: { 
          num: number, 
          offset: offset
        },
    }).done(function(data){
      callback(data);
    }).fail(function(jqXHR, textStatus){
      console.error(textStatus);
    });
  }

  function showBlocks(data) {
    var $tbody = $browseBlocksTable.find("tbody");
    $tbody.empty();
    _.each(data, function(block) {
        block.age = moment.unix(block.time).fromNow();
        $browseBlocksPlaceholder.remove();
        $tbody.append(blockTemplate(block));
    });
  }

  if($browseBlocksTable.length > 0) {
    getBlocks(BLOCKS_PER_PAGE, 0, showBlocks);
  }

  $searchInput.on("keydown", function(e) {
    if (!e) { var e = window.event; }

    // Enter is pressed
    if (e.keyCode == 13) { 
      try_search();
    }
  });


  function try_search() {
    $.ajax({
      url: '/search/' + $searchInput.val()
    }).done(function(data){
      if(data.url) {
        window.location=data.url;
      }
    }).fail(function(jqXHR, textStatus){
      console.error(textStatus);
    });
  }

  $searchButton.click(function(e){
    e.preventDefault();
    try_search();
  });

  if($blockTransactions.length > 0) {
    var blockTransactionsUrl = window.location.pathname + "/transactions";
    $.ajax({
      url: blockTransactionsUrl,
      type: "get"
    }).done(function(data){
      _.each(data, function(transaction){
        transaction.time = moment.unix(transaction.time).format();
        $blockTransactions.append(transactionDetailsTemplate(transaction));
      });
    }).fail(function(jqXHR, textStatus){
      console.error(textStatus);
    });
  }
})
